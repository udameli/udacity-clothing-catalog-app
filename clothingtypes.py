from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models import Type, Base

engine = create_engine('postgresql://postgres:postgres@localhost/clothingcatalog.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind = engine)
session = DBSession()

# Add clothing types
type1 = Type(type = 'coats')

session.add(type1)
session.commit()

type2 = Type(type = 'dresses')
session.add(type2)
session.commit()

type3 = Type(type = 'skirts')
session.add(type3)
session.commit()

type4 = Type(type = 'sweaters')
session.add(type4)
session.commit()

type5 = Type(type = 'shirts')
session.add(type5)
session.commit()

type6 = Type(type = 'shoes')
session.add(type6)
session.commit()

type7 = Type(type = 'accessories')
session.add(type7)
session.commit()

type8 = Type(type = 'bags')
session.add(type8)
session.commit()