from sqlalchemy import Column, Integer, String, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy import create_engine

Base = declarative_base()

class User(Base):
	__tablename__ = 'user'
	id = Column(Integer, primary_key = True)
	username = Column(String(64), nullable = False)
	email = Column(String, index = True, nullable = False)

class Type(Base):
	__tablename__ = 'type'
	id = Column(Integer, primary_key = True)
	type = Column(String, nullable = False)

	@property
	def serialize(self):
		# Return object data in JSON format
		return {
			'id': self.id,
			'type': self.type,
		}

class Item(Base):
	__tablename__ = 'item'
	id = Column(Integer, primary_key = True)
	name = Column(String(20), nullable = False)
	description = Column(Text, nullable = False)
	img_path = Column(String(500), nullable = False)
	type_id = Column(Integer, ForeignKey('type.id'), nullable = False)
	type = relationship(Type)
	user_id = Column(Integer, ForeignKey('user.id'), nullable = False)
	user = relationship(User)

	@property
	def serialize(self):
		# Return object data in JSON format
		return {
			'id': self.id,
			'name': self.name,
			'description': self.description,
			'img_path': self.img_path,
			'type_id': self.type_id,
			'user_id': self.user_id
		}

engine = create_engine('postgresql://catalog:catalog@localhost/catalog')

Base.metadata.create_all(engine)

