from src.config import PROJECT_ROOT, _resolve_project_path


def test_relative_local_database_path_is_anchored_to_project_root():
    assert _resolve_project_path("var/test.db") == (
        PROJECT_ROOT / "var" / "test.db"
    ).resolve()


def test_absolute_local_database_path_is_preserved(tmp_path):
    database_path = tmp_path / "test.db"
    assert _resolve_project_path(database_path) == database_path
