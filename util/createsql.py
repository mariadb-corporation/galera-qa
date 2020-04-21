import random
from util import datagen
import sys

# data_type List
data_type = ['int', 'bigint', 'char', 'varchar', 'date', 'float', 'double', 'text', 'time', 'timestamp']
# CREATE TABLE extra options list
key_type = ['pk', 'uk']
# Table name List
table_names = ['t1', 't2', 't3', 't4', 't5', 't6', 't7', 't8', 't9', 't10']
# Column name list
column_names = ['c1', 'c2', 'c3', 'c4', 'c5', 'c6', 'c7', 'c8', 'c9', 'c10']
# Char count list
varchar_count = [32, 64, 126, 256, 1024]


class GenerateSQL:
    def __init__(self, filename, lines):
        self.filename = filename
        self.lines = lines
        self.table_count = random.randint(1, len(table_names))
        self.column_count = random.randint(1, len(column_names))
        self.insert_sql_count = int(((self.lines / self.table_count) - 1))
        
    def OutFile(self):
        sys.stdout = open(self.filename, "w")

    def OptSelection(self, myextra):
        if myextra == "pk":
            return "PRIMARY KEY"
        elif myextra == "uk":
            return "UNIQUE"
        else:
            return ""

    def CreateTable(self):
        # Create table with random data.
        for i in range(self.table_count):
            data_types = ""
            index_length = ""
            typearray = []
            table_name = table_names[i]
            for j in range(self.column_count):
                column_description = random.choice(data_type)
                typearray.append(column_description)
                if j == 0:
                    if column_description == "text":
                        index_length = "(10)"
                if column_description == "char":
                    column_description = column_description + " (1)"
                if column_description == "varchar":
                    column_description = column_description + " (" + format(random.choice(varchar_count)) + ")"
                if column_description == "timestamp":
                    column_description = column_description + " DEFAULT CURRENT_TIMESTAMP "
                data_types += column_names[j] + " " + column_description + ", "
            print("CREATE TABLE IF NOT EXISTS " + table_name + "( " + data_types + 
                  " primary key (c1" + index_length + ") );")
            for j in range(self.insert_sql_count):
                data_value = ""
                for column_description in typearray:
                    text = datagen.DataGenerator(column_description)
                    data_value += "'" + text.getData() + "', "
                data_value = data_value[:-2]
                print("INSERT INTO " + table_name + " values (" + data_value + ");")

    def DropTable(self):
        for i in range(self.table_count):
            table_name = table_names[i]
            print("DROP TABLE IF EXISTS " + table_name + ";")
