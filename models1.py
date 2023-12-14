from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Printer(Base):
    __tablename__ = "tbl_print"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    tipe = Column(String(100))
    namaprinter = Column(String(100))
    kecepatancetak = Column(String(100))
    harga = Column(Integer)
    resolusicetak = Column(String(100))

    def __init__(self, tipe, namaprinter, kecepatancetak, harga, resolusicetak):
        self.tipe = tipe
        self.namaprinter = namaprinter
        self.kecepatancetak = kecepatancetak
        self.harga = harga
        self.resolusicetak = resolusicetak

    def calculate_score(self, dev_scale):
        score = 0
        score += self.tipe * dev_scale['tipe']
        score += self.namaprinter * dev_scale['namaprinter']
        score += self.kecepatancetak * dev_scale['kecepatancetak']
        score -= self.harga * dev_scale['harga']
        score += self.resolusicetak * dev_scale['resolusicetak']
        
        return score

    def __repr__(self):
        return f"printer(id={self.id!r}, tipe={self.tipe!r}, namaprinter={self.namaprinter!r}, kecepatancetak={self.kecepatancetak!r}, harga={self.harga!r}, resolusicetak={self.resolusicetak!r})"