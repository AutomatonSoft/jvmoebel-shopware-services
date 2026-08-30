from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, declared_attr
from core.config import settings


engine = create_async_engine(
    settings.db.url,  # URL берём из твоего Settings
    echo=settings.db.echo,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

async_session_maker = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    __abstract__ = True

    @declared_attr.directive
    def __tablename__(cls) -> str:
        return f"{cls.__name__.lower()}s"

    id: Mapped[int] = mapped_column(primary_key=True)


async def get_async_session() -> AsyncSession:
    """Yield an async database session для FastAPI dependency injection."""
    async with async_session_maker() as session:
        yield session