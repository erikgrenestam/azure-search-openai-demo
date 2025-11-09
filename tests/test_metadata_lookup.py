import pytest
from unittest.mock import AsyncMock, MagicMock
from prepdocslib.filestrategy import FileStrategy

@pytest.mark.asyncio
async def test_load_metadata_lookup_json(monkeypatch):
    # Mock ListFileStrategy and its list() method
    mock_file = MagicMock()
    mock_file.filename.return_value = "metadata.json"
    mock_file.content.read.return_value = b'[{"downloaded_filename": "file1", "content_type": "pdf", "date": "2024-01-01", "topic": "test"}]'
    mock_file.close = MagicMock()
    mock_list_file_strategy = MagicMock()
    mock_list_file_strategy.list.return_value = AsyncMock(return_value=iter([mock_file]))

    # Instantiate FileStrategy with mocks
    fs = FileStrategy(
        list_file_strategy=mock_list_file_strategy,
        blob_manager=None,
        search_info=None,
        file_processors={},
    )

    result = await fs.load_metadata_lookup()
    assert isinstance(result, dict)
    assert len(result) > 0