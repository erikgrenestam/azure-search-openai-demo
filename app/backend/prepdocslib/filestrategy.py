import logging
import json  # Added import
import os
from typing import Optional

from azure.core.credentials import AzureKeyCredential

from .blobmanager import BlobManager
from .embeddings import ImageEmbeddings, OpenAIEmbeddings
from .fileprocessor import FileProcessor
from .listfilestrategy import File, ListFileStrategy
from .mediadescriber import ContentUnderstandingDescriber
from .searchmanager import SearchManager, Section
from .strategy import DocumentAction, SearchInfo, Strategy

logger = logging.getLogger("scripts")


async def parse_file(
    file: File,
    file_processors: dict[str, FileProcessor],
    category: Optional[str] = None,
    image_embeddings: Optional[ImageEmbeddings] = None,
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
    logger.info("Splitting '%s' into sections", file.filename())
    if image_embeddings:
        logger.warning("Each page will be split into smaller chunks of text, but images will be of the entire page.")
    sections = [
        Section(split_page, content=file, category=category, publication_date=publication_date, topic=topic)
        for split_page in processor.splitter.split_pages(pages)
    ]
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
        use_content_understanding: bool = False,
        content_understanding_endpoint: Optional[str] = None,
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
        self.use_content_understanding = use_content_understanding
        self.content_understanding_endpoint = content_understanding_endpoint

    def setup_search_manager(self):
        self.search_manager = SearchManager(
            self.search_info,
            self.search_analyzer_name,
            self.use_acls,
            False,
            self.embeddings,
            field_name_embedding=self.search_field_name_embedding,
            search_images=self.image_embeddings is not None,
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
            connection_string = os.getenv("MSSQL_CONNECTION_STRING")
            if connection_string:
                logger.info("Attempting to load metadata from MSSQL database")
                try:
                    import pyodbc
                    with pyodbc.connect(connection_string) as conn:
                        cursor = conn.cursor()
                        # Adjust the query based on your actual table structure
                        query = """
                        SELECT downloaded_filename, content_type, publication_date, topic 
                        FROM metadata_table
                        """
                        cursor.execute(query)
                        rows = cursor.fetchall()
                        
                        metadata_lookup = {
                            row.downloaded_filename: {
                                "content_type": row.content_type,
                                "publication_date": row.publication_date,
                                "topic": row.topic,
                            }
                            for row in rows
                            if row.downloaded_filename
                        }
                        logger.info(f"Successfully loaded {len(metadata_lookup)} metadata records from MSSQL database")
                        return metadata_lookup
                except ImportError:
                    logger.warning("pyodbc not available, falling back to JSON file for metadata")
            else:
                logger.info("No MSSQL connection string found, will try JSON file")
        except Exception as e:
            logger.warning(f"Failed to load metadata from MSSQL database: {e}, falling back to JSON file")
        
        # Fallback: try to load from JSON file in the same directory as the files
        try:
            logger.info("Attempting to load metadata from JSON file")
            
            # Use the list_file_strategy to find metadata.json file
            files = self.list_file_strategy.list()
            metadata_file = None
            
            async for file in files:
                try:
                    if file.filename().lower() == "metadata.json":
                        metadata_file = file
                        break
                finally:
                    if file.filename().lower() != "metadata.json":
                        file.close()
            
            if metadata_file:
                logger.info(f"Found metadata.json file: {metadata_file.filename()}")
                # Read the content properly depending on the type
                if hasattr(metadata_file.content, 'read'):
                    content_str = metadata_file.content.read()
                    if isinstance(content_str, bytes):
                        content_str = content_str.decode('utf-8')
                else:
                    content_str = str(metadata_file.content)
                
                metadata_content = json.loads(content_str)
                metadata_file.close()
                
                # Create lookup dictionary from JSON content
                if isinstance(metadata_content, list):
                    metadata_lookup = {
                        item.get("downloaded_filename"): {
                            "content_type": item.get("content_type"),
                            "publication_date": item.get("date"),
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
                logger.warning("No metadata.json file found in the file directory")
                
        except Exception as e:
            logger.error(f"Failed to load metadata from JSON file: {e}")
        
        return metadata_lookup

    async def setup(self):
        self.setup_search_manager()
        await self.search_manager.create_index()

        if self.use_content_understanding:
            if self.content_understanding_endpoint is None:
                raise ValueError("Content Understanding is enabled but no endpoint was provided")
            if isinstance(self.search_info.credential, AzureKeyCredential):
                raise ValueError(
                    "AzureKeyCredential is not supported for Content Understanding, use keyless auth instead"
                )
            cu_manager = ContentUnderstandingDescriber(self.content_understanding_endpoint, self.search_info.credential)
            await cu_manager.create_analyzer()

    async def run(self):
        self.setup_search_manager()
        if self.document_action == DocumentAction.Add:
            # Load metadata using the new method
            metadata_lookup = await self.load_metadata_lookup()

            files = self.list_file_strategy.list()
            async for file in files:
                try:
                    # Skip metadata.json file during processing
                    if file.filename().lower() == "metadata.json":
                        file.close()
                        continue
                        
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

                    sections = await parse_file(
                        file,
                        self.file_processors,
                        file_category,
                        self.image_embeddings,
                        publication_date,
                        topics,
                    )
                    if sections:
                        blob_sas_uris = await self.blob_manager.upload_blob(file)
                        blob_image_embeddings: Optional[list[list[float]]] = None
                        if self.image_embeddings and blob_sas_uris:
                            blob_image_embeddings = await self.image_embeddings.create_embeddings(blob_sas_uris)
                        await self.search_manager.update_content(sections, blob_image_embeddings, url=file.url)
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
        embeddings: Optional[OpenAIEmbeddings] = None,
        image_embeddings: Optional[ImageEmbeddings] = None,
        search_field_name_embedding: Optional[str] = None,
    ):
        self.file_processors = file_processors
        self.embeddings = embeddings
        self.image_embeddings = image_embeddings
        self.search_info = search_info
        self.search_manager = SearchManager(
            search_info=self.search_info,
            search_analyzer_name=None,
            use_acls=True,
            use_int_vectorization=False,
            embeddings=self.embeddings,
            field_name_embedding=search_field_name_embedding,
            search_images=False,
        )
        self.search_field_name_embedding = search_field_name_embedding

    async def add_file(self, file: File):
        if self.image_embeddings:
            logging.warning("Image embeddings are not currently supported for the user upload feature")
        sections = await parse_file(file, self.file_processors)
        if sections:
            await self.search_manager.update_content(sections, url=file.url)

    async def remove_file(self, filename: str, oid: str):
        if filename is None or filename == "":
            logging.warning("Filename is required to remove a file")
            return
        await self.search_manager.remove_content(filename, oid)
