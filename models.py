from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine

Base = declarative_base()


class User(Base):
    __tablename__ = 'user'
    id = Column(Integer, primary_key=True)
    name = Column(String(250))
    email = Column(String(250))
    categories = relationship("Category", cascade="save-update, delete, delete-orphan")
    items = relationship("Item", cascade="save-update, delete, delete-orphan")

    @property
    def serialize(self):
        return {
            'name': self.name,
            'email': self.email,
            'id': self.id
        }


class Category(Base):
    __tablename__ = 'category'
    name = Column(String(250), index=True)
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('user.id'))
    items = relationship("Item", cascade="delete, delete-orphan")

    @property
    def serialize(self):
        return {
            'name': self.name,
            'id': self.id
        }


class Item(Base):
    __tablename__ = 'item'
    id = Column(Integer, primary_key=True)
    name = Column(String(250))
    description = Column(String(250))
    category_id = Column(Integer, ForeignKey('category.id'))
    user_id = Column(Integer, ForeignKey('user.id'))

    @property
    def serialize(self):
        return {
            'name': self.name,
            'description': self.description,
            'id': self.id
        }


engine = create_engine('sqlite:///itemCatalog.db')

Base.metadata.create_all(engine)
