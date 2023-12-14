from sqlalchemy import String, Integer, Column
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class printer(Base):
    __tablename__ = "tbl_print"
    id = Column(Integer, primary_key=True)
    tipe = Column(String)
    namaprinter = Column(String)
    kecepatancetak = Column(String)
    harga = Column(String)
    resolusicetak = Column(String)

    def __repr__(self):
        return f"printer(tipe={self.tipe!r}, namaprinter={self.namaprinter!r}, kecepatancetak={self.kecepatancetak!r}, harga={self.harga!r}, resolusicetak={self.resolusicetak!r})"