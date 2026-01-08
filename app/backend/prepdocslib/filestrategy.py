import logging
import json  # Added import
import os
from datetime import datetime
from typing import Optional

from .blobmanager import AdlsBlobManager, BaseBlobManager, BlobManager
from .embeddings import ImageEmbeddings, OpenAIEmbeddings
from .figureprocessor import (
    FigureProcessor,
    MediaDescriptionStrategy,
    process_page_image,
)
from .fileprocessor import FileProcessor
from .listfilestrategy import File, ListFileStrategy
from .mediadescriber import ContentUnderstandingDescriber
from .searchmanager import SearchManager, Section
from .strategy import DocumentAction, SearchInfo, Strategy
from .textprocessor import process_text

logger = logging.getLogger("scripts")


def convert_timestamp_to_iso8601(timestamp) -> Optional[str]:
    """
    Convert Unix timestamp (milliseconds) to ISO 8601 format for Azure Search.
    
    Args:
        timestamp: Unix timestamp in milliseconds (int) or ISO 8601 string or None
    
    Returns:
        ISO 8601 formatted string or None
    """
    if timestamp is None or timestamp == '':
        return None
    
    # If already a string, check if it's in ISO format
    if isinstance(timestamp, str):
        # If it contains 'T' or '-', assume it's already in ISO format
        if 'T' in timestamp or timestamp.count('-') >= 2:
            return timestamp
        # Otherwise try to parse as timestamp string
        try:
            timestamp = int(timestamp)
        except ValueError:
            logger.warning(f"Could not parse publication_date: {timestamp}")
            return None
    
    # Convert Unix timestamp (milliseconds) to ISO 8601
    try:
        dt = datetime.fromtimestamp(timestamp / 1000.0)
        return dt.strftime('%Y-%m-%dT%H:%M:%SZ')
    except (ValueError, TypeError, OSError) as e:
        logger.warning(f"Could not convert publication_date timestamp {timestamp}: {e}")
        return None


async def parse_file(
    file: File,
    file_processors: dict[str, FileProcessor],
    category: Optional[str] = None,
    blob_manager: Optional[BaseBlobManager] = None,
    image_embeddings_client: Optional[ImageEmbeddings] = None,
    figure_processor: Optional[FigureProcessor] = None,
    user_oid: Optional[str] = None,
    publication_date: Optional[str] = None,
    topic: Optional[list[str]] = None,
) -> list[Section]:

    key = file.file_extension().lower()
    processor = file_processors.get(key)
    if processor is None:
        logger.info("Skipping '%s', no parser found.", file.filename())
        return []
    logger.info("Ingesting '%s'", file.filename())
    pages = [page async for page in processor.parser.parse(content=file.content)]
    for page in pages:
        for image in page.images:
            logger.info("Processing image '%s' on page %d", image.filename, page.page_num)
            await process_page_image(
                image=image,
                document_filename=file.filename(),
                blob_manager=blob_manager,
                image_embeddings_client=image_embeddings_client,
                figure_processor=figure_processor,
                user_oid=user_oid,
            )
    sections = process_text(pages, file, processor.splitter, category=category, publication_date=publication_date, topic=topic)
    return sections


class FileStrategy(Strategy):
    """
    Strategy for ingesting documents into a search service from files stored either locally or in a data lake storage account
    """

    def __init__(
        self,
        list_file_strategy: ListFileStrategy,
        blob_manager: BlobManager,
        search_info: SearchInfo,
        file_processors: dict[str, FileProcessor],
        document_action: DocumentAction = DocumentAction.Add,
        embeddings: Optional[OpenAIEmbeddings] = None,
        image_embeddings: Optional[ImageEmbeddings] = None,
        search_analyzer_name: Optional[str] = None,
        search_field_name_embedding: Optional[str] = None,
        use_acls: bool = False,
        category: Optional[str] = None,
        figure_processor: Optional[FigureProcessor] = None,
        enforce_access_control: bool = False,
        use_web_source: bool = False,
        use_sharepoint_source: bool = False,
        embedding_batch_delay_seconds: float = 2,
    ):
        self.list_file_strategy = list_file_strategy
        self.blob_manager = blob_manager
        self.file_processors = file_processors
        self.document_action = document_action
        self.embeddings = embeddings
        self.image_embeddings = image_embeddings
        self.search_analyzer_name = search_analyzer_name
        self.search_field_name_embedding = search_field_name_embedding
        self.search_info = search_info
        self.use_acls = use_acls
        self.category = category
        self.figure_processor = figure_processor
        self.enforce_access_control = enforce_access_control
        self.use_web_source = use_web_source
        self.use_sharepoint_source = use_sharepoint_source
        self.embedding_batch_delay_seconds = embedding_batch_delay_seconds

    def setup_search_manager(self):
        self.search_manager = SearchManager(
            self.search_info,
            self.search_analyzer_name,
            self.use_acls,
            False,  # use_parent_index_projection disabled for file-based ingestion
            self.embeddings,
            field_name_embedding=self.search_field_name_embedding,
            search_images=self.image_embeddings is not None,
            enforce_access_control=self.enforce_access_control,
            use_web_source=self.use_web_source,
            use_sharepoint_source=self.use_sharepoint_source,
            embedding_batch_delay_seconds=self.embedding_batch_delay_seconds,
        )

    async def load_metadata_lookup(self) -> dict:
        """
        Load metadata lookup dictionary, first trying MSSQL database, then falling back to JSON file.
        
        Returns:
            dict: Metadata lookup dictionary with filename as key and metadata as value
        """
        metadata_lookup = {}
        
        # First try to load from MSSQL database
        try:
            logger.info("Attempting to load metadata from MSSQL database")
            try:
                from dnsql import DNSQL

                query = """
                SELECT downloaded_filename, content_type, publication_date, topic 
                FROM area102.dn_publication_metadata
                """
                metadata_df = DNSQL.execute_query(query)
                
                metadata_lookup = {
                    row.downloaded_filename: {
                        "content_type": row.content_type,
                        "publication_date": convert_timestamp_to_iso8601(row.publication_date),
                        "topic": row.topic,
                    }
                    for row in metadata_df.iterrows()
                    if row.downloaded_filename
                }
                logger.info(f"Successfully loaded {len(metadata_lookup)} metadata records from MSSQL database")
                return metadata_lookup
            except ImportError:
                logger.warning("dnsql not available, falling back to JSON file for metadata")
        except Exception as e:
            logger.warning(f"Failed to load metadata from MSSQL database: {e}, falling back to JSON file")
        
        # Fallback: try to load from JSON file in the same directory as the files
        try:
            logger.info("Attempting to load metadata from JSON file")
            
            # Check if list_file_strategy has metadata_file attribute
            metadata_file_path = getattr(self.list_file_strategy, 'metadata_file', None)
            
            # If metadata_file_path is provided and exists, use it directly
            if metadata_file_path and os.path.exists(metadata_file_path):
                logger.info(f"Loading metadata from provided path: {metadata_file_path}")
                with open(metadata_file_path, 'r', encoding='utf-8') as f:
                    metadata_content = json.load(f)

                # Create lookup dictionary from JSON content
                if isinstance(metadata_content, list):
                    metadata_lookup = {
                        item.get("downloaded_filename"): {
                            "content_type": item.get("content_type"),
                            "publication_date": convert_timestamp_to_iso8601(item.get("publication_date")),
                            "topic": item.get("topic"),
                        }
                        for item in metadata_content
                        if item.get("downloaded_filename")
                    }
                else:
                    # If it's a direct mapping
                    metadata_lookup = metadata_content
            
                logger.info(f"Successfully loaded {len(metadata_lookup)} metadata records from JSON file")
            else:
                logger.warning("No metadata json file found.")
                
        except Exception as e:
            logger.error(f"Failed to load metadata from JSON file: {e}")
        
        return metadata_lookup

    async def setup(self):
        self.setup_search_manager()
        await self.search_manager.create_index()

        if (
            self.figure_processor is not None
            and self.figure_processor.strategy == MediaDescriptionStrategy.CONTENTUNDERSTANDING
        ):
            media_describer = await self.figure_processor.get_media_describer()
            if isinstance(media_describer, ContentUnderstandingDescriber):
                await media_describer.create_analyzer()
                self.figure_processor.mark_content_understanding_ready()

    async def run(self):
        self.setup_search_manager()
        if self.document_action == DocumentAction.Add:
            # Load metadata
            metadata_lookup = await self.load_metadata_lookup()

            files = self.list_file_strategy.list()
            async for file in files:
                try:
                    # Skip metadata.json file during processing
                    if file.filename().lower() == "metadata_records.json":
                        file.close()
                        continue
                    
                    # Store the original local path before upload (for MD5 hash writing)
                    local_file_path = file.url
                        
                    # Determine category for the current file
                    metadata = metadata_lookup.get(file.filename())
                    file_category = metadata.get("content_type") if metadata else None
                    if not file_category:
                        file_category = self.category  # Fallback to the global category

                    publication_date = metadata.get("publication_date") if metadata else None
                    if publication_date == '':
                        publication_date = None
                    topic_str = metadata.get("topic") if metadata else None
                    topics = [t.strip() for t in topic_str.split(",")] if topic_str else []
                    blob_url = await self.blob_manager.upload_blob(file)
                    sections = await parse_file(
                        file,
                        self.file_processors,
                        file_category,
                        self.blob_manager,
                        self.image_embeddings,
                        figure_processor=self.figure_processor,
                        publication_date=publication_date,
                        topic=topics
                    )
                    if sections:
                        await self.search_manager.update_content(sections, url=blob_url)
                        # Write MD5 hash after successful processing
                        if local_file_path:
                            self.list_file_strategy.write_md5(local_file_path)
                finally:
                    if file:
                        file.close()
        elif self.document_action == DocumentAction.Remove:
            paths = self.list_file_strategy.list_paths()
            async for path in paths:
                await self.blob_manager.remove_blob(path)
                await self.search_manager.remove_content(path)
        elif self.document_action == DocumentAction.RemoveAll:
            await self.blob_manager.remove_blob()
            await self.search_manager.remove_content()


class UploadUserFileStrategy:
    """
    Strategy for ingesting a file that has already been uploaded to a ADLS2 storage account
    """

    def __init__(
        self,
        search_info: SearchInfo,
        file_processors: dict[str, FileProcessor],
        blob_manager: AdlsBlobManager,
        search_field_name_embedding: Optional[str] = None,
        embeddings: Optional[OpenAIEmbeddings] = None,
        image_embeddings: Optional[ImageEmbeddings] = None,
        enforce_access_control: bool = False,
        figure_processor: Optional[FigureProcessor] = None,
    ):
        self.file_processors = file_processors
        self.embeddings = embeddings
        self.image_embeddings = image_embeddings
        self.search_info = search_info
        self.blob_manager = blob_manager
        self.figure_processor = figure_processor
        self.search_manager = SearchManager(
            search_info=self.search_info,
            search_analyzer_name=None,
            use_acls=True,
            use_parent_index_projection=False,
            embeddings=self.embeddings,
            field_name_embedding=search_field_name_embedding,
            search_images=image_embeddings is not None,
            enforce_access_control=enforce_access_control,
        )
        self.search_field_name_embedding = search_field_name_embedding

    async def add_file(self, file: File, user_oid: str):
        sections = await parse_file(
            file,
            self.file_processors,
            None,
            self.blob_manager,
            self.image_embeddings,
            figure_processor=self.figure_processor,
            user_oid=user_oid,
            publication_date=None,
            topic=None
        )
        if sections:
            await self.search_manager.update_content(sections, url=file.url)

    async def remove_file(self, filename: str, oid: str):
        if filename is None or filename == "":
            logging.warning("Filename is required to remove a file")
            return
        await self.search_manager.remove_content(filename, oid)
