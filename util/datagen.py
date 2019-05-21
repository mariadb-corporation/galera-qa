import random
import string
from datetime import datetime, timedelta

date_format = ["%B %d, %Y", "%Y-%m-%d", "%d/%m/%Y", "%d/%m/%y",
               "%Y-%b-%d", "%b-%d-%Y", "%d-%b-%Y", "%y-%b-%d",
               "%b-%d-%y", "%d-%b-%y", "%Y%m%d", "%y%m%d"]
time_format = ["%T", "%H:%M", "%H%M%S", "%T.%f", "%T %p"]


class DataGenerator:
    def __init__(self, data_type):
        self.data_type = data_type
        
    def gen_datetime(self, min_year=1900, max_year=datetime.now().year):
        # generate a datetime in format yyyy-mm-dd hh:mm:ss.000000
        start = datetime(min_year, 1, 1, 00, 00, 00)
        years = max_year - min_year + 1
        end = start + timedelta(days=365 * years)
        return start + (end - start) * random.random()

    def getData(self):
        if self.data_type == "int" or self.data_type == "bigint" or self.data_type == "float":
            data = ''.join(random.choices(string.digits, k=random.randint(1, 20)))
            return data
        elif self.data_type == "char":
            data = ''.join(random.choices(string.ascii_letters, k=random.randint(1, 1)))
            return data
        elif self.data_type == "varchar":
            data = ''.join(random.choices(string.ascii_letters, k=random.randint(1, 20)))
            return data
        elif self.data_type == "text":
            data = ''.join(random.choices(string.ascii_letters + string.digits, k=random.randint(1, 50)))
            return data
        elif self.data_type == "date":
            data = self.gen_datetime().strftime(date_format[random.randint(0, 11)])
            return data
        elif self.data_type == "time":
            data = self.gen_datetime().strftime(time_format[random.randint(0, 4)])
            return data
        elif self.data_type == "timestamp" :
            data = self.gen_datetime().strftime(date_format[random.randint(0, 11)]) + \
                   " " + self.gen_datetime().strftime(time_format[random.randint(0, 4)])
            return data
        else:
            return "sampledata"
