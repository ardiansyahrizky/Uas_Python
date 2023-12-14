from http import HTTPStatus
from flask import Flask, request, abort
from flask_restful import Resource, Api
from models import printer as printerModel
from engine import engine
from sqlalchemy import select
from sqlalchemy.orm import Session
from tabulate import tabulate

session = Session(engine)

app = Flask(__name__)
api = Api(app)


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
        query = select(printerModel.id, printerModel.tipe, printerModel.namaprinter, printerModel.kecepatancetak, printerModel.harga,
                       printerModel.resolusicetak)
        result = session.execute(query).fetchall()
        return [{'id': printer.id, 'tipe': printer.tipe, 'namaprinter': printer.namaprinter, 'kecepatancetak': printer.kecepatancetak,
                'harga': printer.harga, 'resolusicetak': printer.resolusicetak} for printer in result]

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


    def update_weights(self, new_weights):
        self.raw_weight = new_weights


class WeightedProductCalculator(BaseMethod):
    def update_weights(self, new_weights):
        self.raw_weight = new_weights

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
                'ID': product['id'],
                'score': round(product['produk'], 3)
            }
            for product in sorted_produk
        ]
        return sorted_data

class WeightedProduct(Resource):
    def get(self):
        calculator = WeightedProductCalculator()
        result = calculator.calculate
        return sorted(result, key=lambda x: x['score'], reverse=True), HTTPStatus.OK.value

    def post(self):
        new_weights = request.get_json()
        calculator = WeightedProductCalculator()
        calculator.update_weights(new_weights)
        result = calculator.calculate
        return {'printer': sorted(result, key=lambda x: x['score'], reverse=True)}, HTTPStatus.OK.value

class SimpleAdditiveWeightingCalculator(BaseMethod):
    @property
    def calculate(self):
        weight = self.weight
        result = [
            {
                'ID': row['id'],
                'Score': round(row['tipe'] * weight['tipe'] +
                            row['namaprinter'] * weight['namaprinter'] +
                            row['kecepatancetak'] * weight['kecepatancetak'] +
                            row['harga'] * weight['harga'] +
                            row['resolusicetak'] * weight['resolusicetak'], 3)
            }
            for row in self.normalized_data
        ]
        sorted_result = sorted(result, key=lambda x: x['Score'], reverse=True)
        return sorted_result

    def update_weights(self, new_weights):
        self.raw_weight = new_weights


class SimpleAdditiveWeighting(Resource):
    def get(self):
        saw = SimpleAdditiveWeightingCalculator()
        result = saw.calculate
        return sorted(result, key=lambda x: x['Score'], reverse=True), HTTPStatus.OK.value

    def post(self):
        new_weights = request.get_json()
        saw = SimpleAdditiveWeightingCalculator()
        saw.update_weights(new_weights)
        result = saw.calculate
        return {'printer': sorted(result, key=lambda x: x['Score'], reverse=True)}, HTTPStatus.OK.value


class print(Resource):
    def get_paginated_result(self, url, list, args):
        page_size = int(args.get('page_size', 10))
        page = int(args.get('page', 1))
        page_count = int((len(list) + page_size - 1) / page_size)
        start = (page - 1) * page_size
        end = min(start + page_size, len(list))

        if page < page_count:
            next_page = f'{url}?page={page+1}&page_size={page_size}'
        else:
            next_page = None
        if page > 1:
            prev_page = f'{url}?page={page-1}&page_size={page_size}'
        else:
            prev_page = None

        if page > page_count or page < 1:
            abort(404, description=f'Data Tidak Ditemukan.')
        return {
            'page': page,
            'page_size': page_size,
            'next': next_page,
            'prev': prev_page,
            'Results': list[start:end]
        }

    def get(self):
        query = session.query(printerModel).order_by(printerModel.id)
        result_set = query.all()
        data = [{'id': row.id, 'tipe': row.tipe, 'namaprinter': row.namaprinter, 'kecepatancetak': row.kecepatancetak,
                 'harga': row.harga, 'resolusicetak': row.resolusicetak}
                for row in result_set]
        return self.get_paginated_result('/printer', data, request.args), 200

api.add_resource(print, '/printer')
api.add_resource(WeightedProduct, '/wp')
api.add_resource(SimpleAdditiveWeighting, '/saw')

if __name__ == '__main__':
    app.run(port='5005', debug=True)