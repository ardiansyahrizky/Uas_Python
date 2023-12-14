import sys
from colorama import Fore, Style
from models import Base, Printer
from engine import engine
from sqlalchemy import select
from sqlalchemy.orm import Session
from tabulate import tabulate
from settings import DEV_SCALE


session = Session(engine)


def create_table():
    Base.metadata.create_all(engine)
    print(f'{Fore.GREEN}[Success]: {Style.RESET_ALL}Database has been created!')


def review_data():
    query = select(Printer)
    for print in session.scalars(query):
        print(print)


class BaseMethod():

    def __init__(self):
        # 1-5
        self.raw_weight = {'tipe': 3, 'namaprinter': 4,
                           'kecepatancetak': 3, 'harga': 4, 'resolusicetak': 5}

    @property
    def weight(self):
        total_weight = sum(self.raw_weight.values())
        return {k: round(v/total_weight, 2) for k, v in self.raw_weight.items()}

    @property
    def data(self):
        query = select(Printer.id, Printer.tipe, Printer.namaprinter, Printer.kecepatancetak, Printer.harga,
                       Printer.resolusicetak)
        result = session.execute(query).fetchall()
        return [{'id': print.id, 'tipe': print.tipe, 'namaprinter': print.namaprinter, 'kecepatancetak': print.kecepatancetak,
                'harga': print.harga, 'resolusicetak': print.resolusicetak} for print in result]

    @property
    def normalized_data(self):
        def extract_numeric_values(spec):
            numeric_values = [float(value.split()[0]) for value in spec.split(',') if value.split()[0].replace('.', '').isdigit()]
            return numeric_values

        def clean_harga_value(harga_str):
            cleaned_str = ''.join(char for char in harga_str if char.isdigit() or char == '.')
            # Remove extra dots except the last one
            dot_count = cleaned_str.count('.')
            if dot_count > 1:
                cleaned_str = cleaned_str.rsplit('.', dot_count - 1)[0] + cleaned_str.rsplit('.', dot_count - 1)[1].replace('.', '')
            return cleaned_str

        tipe_values = [max(extract_numeric_values(data['tipe']), default=1) for data in self.data]
        namaprinter_values = [max(extract_numeric_values(data['namaprinter']), default=1) for data in self.data]
        kecepatancetak_values = [max(extract_numeric_values(data['kecepatancetak']), default=1) for data in self.data]

        # Harga
        harga_values = [float(clean_harga_value(data['harga'])) if 'harga' in data else 0 for data in self.data]

        resolusicetak_values = [max(extract_numeric_values(data['resolusicetak']), default=1) for data in self.data]

        max_harga_value = max(harga_values) if harga_values else 1

        normalized_data = [
            {
                'id': data['id'],
                'tipe': tipe_value / max(tipe_values),
                'namaprinter': namaprinter_value / max(namaprinter_values),
                'kecepatancetak': kecepatancetak_value / max(kecepatancetak_values),
                'harga': min(harga_values) / max_harga_value if max_harga_value != 0 else 0,
                'resolusicetak': resolusicetak_value / max(resolusicetak_values)
            }
            for data, tipe_value, namaprinter_value, kecepatancetak_value, resolusicetak_value
            in zip(self.data, tipe_values, namaprinter_values, kecepatancetak_values, resolusicetak_values)
        ]

        return normalized_data



class WeightedProduct(BaseMethod):
    @property
    def calculate(self):
        normalized_data = self.normalized_data
        produk = [
            {
                'id': row['id'],
                'produk': row['tipe'] ** self.weight['tipe'] *
                          row['namaprinter'] ** self.weight['namaprinter'] *
                          row['kecepatancetak'] ** self.weight['kecepatancetak'] *
                          row['harga'] ** self.weight['harga'] *
                          row['resolusicetak'] ** self.weight['resolusicetak']
            }
            for row in normalized_data
        ]
        sorted_produk = sorted(produk, key=lambda x: x['produk'], reverse=True)
        sorted_data = [
            {
                'id': product['id'],
                'tipe': product['produk'] / self.weight['tipe'],
                'namaprinter': product['produk'] / self.weight['namaprinter'],
                'kecepatancetak': product['produk'] / self.weight['kecepatancetak'],
                'harga': product['produk'] / self.weight['harga'],
                'resolusicetak': product['produk'] / self.weight['resolusicetak'],
                'score': product['produk']  # Nilai skor akhir
            }
            for product in sorted_produk
        ]
        return sorted_data


class SimpleAdditiveWeighting(BaseMethod):
    @property
    def calculate(self):
        normalized_data = self.normalized_data
        weight = self.weight
        result = {row['id']:
                      round(row['tipe'] * weight['tipe'] +
                            row['namaprinter'] * weight['namaprinter'] +
                            row['kecepatancetak'] * weight['kecepatancetak'] +
                            row['harga'] * weight['harga'] +
                            row['resolusicetak'] * weight['resolusicetak'], 2)
                  for row in normalized_data
                  }
        sorted_result = dict(
            sorted(result.items(), key=lambda x: x[1], reverse=True))
        return sorted_result

def run_saw():
    saw = SimpleAdditiveWeighting()
    result = saw.calculate
    print(tabulate([(k, v) for k, v in result.items()], headers=['ID', 'Score'], tablefmt='pretty'))


def run_wp():
    wp = WeightedProduct()
    result = wp.calculate
    headers = result[0].keys()
    rows = [
        {k: round(v, 4) if isinstance(v, float) else v for k, v in val.items()}
        for val in result
    ]
    print(tabulate(rows, headers="keys", tablefmt="grid"))


if __name__ == "__main__":
    if len(sys.argv) > 1:
        arg = sys.argv[1]

        if arg == 'create_table':
            create_table()
        elif arg == 'review_data':
            review_data()
        elif arg == 'saw':
            run_saw()
        elif arg == 'wp':
            run_wp()
        else:
            print('Command not found')
    else:
        print('Please provide a command')
