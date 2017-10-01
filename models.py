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

	@property
	def serialize(self):
		return {
			'name': self.name,
			'email': self.email,
			'id': self.id
		}

class Category(Base):
	__tablename__ = 'category'
	id = Column(Integer, primary_key=True)
	name = Column(String(250), index=True)
	user_id = Column(Integer, ForeignKey('user.id'))
	user = relationship(User)
	
	@property
	def serialize(self):
		return {
			'name': self.name,
			'id': self.id,
		}


class Item(Base):
	__tablename__ = 'item'
	id = Column(Integer, primary_key=True)
	name = Column(String(250))
	description = Column(String(250))
	category_id = Column(Integer, ForeignKey('category.id'))
	category = relationship("Category")
	user_id = Column(Integer, ForeignKey('user.id'))
	user = relationship(User)

	@property
	def serialize(self):
		return {
			'name': self.name,
			'description': self.description,
			'id': self.id,
			'category_id': self.category_id
		}


engine = create_engine('sqlite:///itemCatalog.db')

Base.metadata.create_all(engine)