def test_news_target_checkpoint_migration_preserves_existing_refresh_state(tmp_path, monkeypatch):
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import create_engine, inspect, text

    url = "sqlite:///" + (tmp_path / "news-checkpoint.db").as_posix()
    monkeypatch.setenv("DATABASE_URL", url)
    config = Config("alembic.ini")
    command.upgrade(config, "20261022_09")
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(text("INSERT INTO refresh_states (user_id, status, news_status) VALUES (1, 'current', 'current')"))

    command.upgrade(config, "head")

    columns = {column["name"] for column in inspect(engine).get_columns("refresh_states")}
    with engine.connect() as connection:
        state = connection.execute(text("SELECT status, news_status, news_asset_tickers, news_industry_ids FROM refresh_states WHERE user_id = 1")).one()
    assert {"news_asset_tickers", "news_industry_ids"}.issubset(columns)
    assert tuple(state) == ("current", "current", "[]", "[]")
    engine.dispose()
