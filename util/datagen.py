import random
import string
from datetime import datetime, timedelta

date_format = ["%Y-%m-%d", "%y-%m-%d"]
time_format = ["%T", "%H:%M", "%H", "%T.%f"]


class DataGenerator:
    def __init__(self, data_type):
        self.data_type = data_type
        
    def gen_datetime(self, min_year=1970, max_year=datetime.now().year):
        # generate a datetime in format yyyy-mm-dd hh:mm:ss.000000
        start = datetime(min_year, 1, 1, 00, 00, 00)
        years = max_year - min_year + 1
        end = start + timedelta(days=365 * years)
        return start + (end - start) * random.random()

    def getData(self):
        # Get random data based on the column type.
        if self.data_type == "int":
            data = ''.join(random.choices(string.digits, k=random.randint(1, 9)))
            return data
        if self.data_type == "bigint":
            data = ''.join(random.choices(string.digits, k=random.randint(1, 15)))
            return data
        elif self.data_type == "float":
            data = str(round(random.uniform(0.0, 1000.9), random.randint(1, 10)))
            return data
        elif self.data_type == "double":
            data = str(round(random.uniform(0.0, 10000.9), random.randint(1, 15)))
            return data
        elif self.data_type == "char":
            data = ''.join(random.choices(string.ascii_letters, k=1))
            return data
        elif self.data_type == "varchar":
            data = ''.join(random.choices(string.ascii_letters, k=random.randint(1, 31)))
            return data
        elif self.data_type == "text":
            data = ''.join(random.choices(string.ascii_letters + string.digits, k=random.randint(1, 50)))
            return data
        elif self.data_type == "date":
            data = self.gen_datetime().strftime(date_format[random.randint(0, 1)])
            return data
        elif self.data_type == "time":
            data = self.gen_datetime().strftime(time_format[random.randint(0, 3)])
            return data
        elif self.data_type == "timestamp":
            data = self.gen_datetime().strftime(date_format[random.randint(0, 1)]) + \
                   " " + self.gen_datetime().strftime(time_format[random.randint(0, 3)])
            return data
        else:
            return "sampledata"
