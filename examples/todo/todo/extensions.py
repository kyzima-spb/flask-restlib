from flask_restlib import RestLib
from flask_restlib.contrib.sqla import SQLAFactory


rest = RestLib(factory=SQLAFactory())
