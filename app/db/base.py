from sqlalchemy.orm import DeclarativeBase, declared_attr


class Base(DeclarativeBase):
    """
    SQLAlchemy 2.0 Declarative Base class.
    All future ARGO tables (floats, profiles, measurements, trajectories)
    will inherit from this Base.
    """
    @declared_attr.directive
    def __tablename__(cls) -> str:
        # Default table name is the lowercased class name
        return cls.__name__.lower()
