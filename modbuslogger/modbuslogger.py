import csv
import minimalmodbus
import serial
from typing import List, Dict, Optional
import serial.tools.list_ports
import psycopg2
import threading
import os


class DataLogger:
    def __init__(self, csv_file: str, port: str, sql_database: Dict):
        """Initialize the DataLogger.
        
        Args:
            csv_file: Path to the CSV file containing metadata.
            port: Serial port to use for Modbus communication.
            sql_database: Dictionary containing database connection details.
            table: Name of the database table to store sensor data.
        """
        self.csv_file = csv_file
        self.port = port
        self.sql_database = sql_database
        self.table = sql_database["table"]
        self.metadata = self._load_metadata()
        self.instruments = {}  # Cache for instrument instances
        # print(self.metadata)
        self.toggle_print = False
        self.toggle_to_database = True # True -> Write to DB, False -> Just Testing

    def _load_metadata(self) -> List[Dict]:
        """Load metadata from the CSV file."""
        metadata = []
        with open(self.csv_file, mode="r") as file:
            reader = csv.DictReader(file)
            for row in reader:
                metadata.append({
                    "ID": int(row["ID"]),
                    "db-name": row["db-name"].split(","),  # Multiple db-names
                    "type": row["type"],
                    "unit": row["unit"].split(","),  # Multiple units
                    "value": row["value"],  # Formula to calculate the value
                    "data_type": row["data_type"].split(","),  # SQL data types
                    "signed": row["signed"] == "True",  # Whether the register is signed or unsigned
                    "registers": int(row["registers"])
                })
        return metadata

    def _read_register(self, address: int, register: int, functioncode: int, signed: bool, registers: int) -> Optional[int]:
        """Read a register using cached instrument instances."""
        for i in range(0,3):
            try:
                if address not in self.instruments:
                    # Create and cache instrument if not exists
                    instrument = minimalmodbus.Instrument(self.port, address)
                    instrument.serial.baudrate = 9600
                    instrument.serial.bytesize = 8
                    instrument.serial.parity = serial.PARITY_NONE
                    instrument.serial.stopbits = 1
                    instrument.serial.timeout = 1.0
                    instrument.mode = minimalmodbus.MODE_RTU
                    instrument.clear_buffers_before_each_transaction = True
                    self.instruments[address] = instrument
                if registers > 1:
                    return self.instruments[address].read_long(
                        register, 
                        functioncode=functioncode, 
                        signed=signed,
                        number_of_registers=registers
                    )
                elif registers == 1:
                    return self.instruments[address].read_register(
                        register, 
                        functioncode=functioncode, 
                        signed=signed
                    )
            except Exception as e:
                print(f"Error {i} reading register {register} from device {address}: {e}")
            
        return None
    

    def _evaluate_formula(self, formula: str, address: int, signed: bool, number_of_registers: int) -> Optional[float]:
        """Evaluate a formula dynamically by replacing register addresses with their values."""
        try:
            # Replace register addresses (e.g., 0x0001) with their actual values
            for part in formula.split():
                if part.startswith("0x"):
                    register = int(part, 16)
                    value = self._read_register(address, register, functioncode=4, signed=signed, registers=number_of_registers)
                    if value is None:
                        return None
                    formula = formula.replace(part, str(value))
            # Evaluate the formula
            return eval(formula)
        except Exception as e:
            print(f"Error evaluating formula '{formula}': {e}")
            return None

    def read_values(self) -> List[Dict]:
        """Read values from the sensors based on the metadata."""
        values = []
        for entry in self.metadata:
            address = entry["ID"]
            formula = entry["value"]
            signed = entry["signed"]
            number_of_registers = entry["registers"]
            calculated_value = self._evaluate_formula(formula, address, signed, number_of_registers)
            if calculated_value is not None:
                values.append({
                    "ID": entry["ID"],
                    "db-name": entry["db-name"],
                    "type": entry["type"],
                    "unit": entry["unit"],
                    "value": calculated_value,
                    "data_type": entry["data_type"]
                })
        return values

    def print_values(self, values: List[Dict]):
        """Print the values for verification, grouped by sensor ID."""
        if self.toggle_print:
            grouped_values = {}
            for entry in values:
                sensor_id = entry["ID"]
                if sensor_id not in grouped_values:
                    grouped_values[sensor_id] = []
                grouped_values[sensor_id].append(entry)

            for sensor_id, entries in grouped_values.items():
                print(f"Sensor ID {sensor_id} ({entries[0]['type']}):")
                for entry in entries:
                    for db_name, unit, value in zip(entry["db-name"], entry["unit"], [entry["value"]] * len(entry["db-name"])):
                        print(f" - {db_name}: {value} {unit}")


    def init_database(self):
        """Initialize the database by creating the table and columns if they don't exist."""
        try:
            connection = psycopg2.connect(user=self.sql_database["user"],
                                        password=self.sql_database["password"],
                                        host=self.sql_database["host"],
                                        port=self.sql_database["port"],
                                        dbname=self.sql_database["dbname"])
            cursor = connection.cursor()

            # Create the table if it doesn't exist
            create_table_query = f"CREATE TABLE IF NOT EXISTS {self.table} (TIME TIMESTAMP WITH TIME ZONE PRIMARY KEY NOT NULL);"
            if self.toggle_print:
                print(f"Query: {create_table_query}")
            if self.toggle_to_database:
                cursor.execute(create_table_query)
                connection.commit()

            # Add columns if they don't exist
            for entry in self.metadata:
                for db_name, data_type in zip(entry["db-name"], entry["data_type"]):
                    add_column_query = f"ALTER TABLE {self.table} ADD COLUMN IF NOT EXISTS {db_name} {data_type};"
                    if self.toggle_print:
                        print(f"Query: {add_column_query}")
                    if self.toggle_to_database:
                        cursor.execute(add_column_query)
                        connection.commit()

        except (Exception, psycopg2.Error) as error:
            print(f"\nDATABASE ERROR: {error}")
        finally:
            if connection:
                cursor.close()
                connection.close()


    def write_to_database(self, values: List[Dict]):
        """Write the values to the database."""
        try:
            connection = psycopg2.connect(user=self.sql_database["user"],
                                        password=self.sql_database["password"],
                                        host=self.sql_database["host"],
                                        port=self.sql_database["port"],
                                        dbname=self.sql_database["dbname"])
            cursor = connection.cursor()

            # Prepare data for insertion
            data = {}
            for entry in values:
                for db_name, value in zip(entry["db-name"], [entry["value"]] * len(entry["db-name"])):
                    data[db_name] = value
            data["TIME"] = "NOW()"

            # Generate the INSERT query with values
            insert_statement = f"INSERT INTO {self.table} ({','.join(data.keys())}) VALUES ({','.join(['%s' for _ in data])});"
            query_with_values = cursor.mogrify(insert_statement, tuple([data[column] for column in data.keys()]))
            if self.toggle_print:
                print(f"Query: {query_with_values.decode('utf-8')}")  # Decode bytes to string for readability

            # Execute the query
            if self.toggle_to_database:
                cursor.execute(insert_statement, tuple([data[column] for column in data.keys()]))
                connection.commit()

        except (Exception, psycopg2.Error) as error:
            print(f"\nDATABASE ERROR: {error}")
        finally:
            if connection:
                cursor.close()
                connection.close()



def find_modbus_port() -> Optional[str]:
    """Scan USB ports for Modbus devices and return the port name if found."""
    ports = serial.tools.list_ports.comports()
    print("Available ports:")
    for port in ports:
        print(f" - {port.device} ({port.description})")
    
    for port in ports:
        print(f"Scanning {port.device} - {port.description}...")
        for address in range(1, 16):  # Check addresses 1-15
            try:
                instrument = minimalmodbus.Instrument(port.device, address)
                instrument.serial.baudrate = 9600
                instrument.serial.timeout = 1.0
                if instrument.read_register(0x0000, functioncode=4) is not None:
                    print(f"Modbus device found on port: {port.device}")
                    return port.device
            except Exception as e:
                print(f"Error scanning {port.device}: {e}")
                continue
    
    print("No Modbus device found on any USB port.")
    return None

# Global interval variable
global INTERVAL

def main():
    # Path to the CSV file containing metadata
    csv_file = "/home/modbuslogger/sensor_metadata.csv"
    
    sql_database = {
        "user": "default_user",
        "password": "changeme987654321",
        "host": "postgres",
        "port": 5432,
        "dbname": "db",
        "table": "modbus_data"
    }
    
    # Find the Modbus device's port
    port = find_modbus_port()
    if not port:
        print("No Modbus device found. Exiting.")
        return
    
    # Initialize the DataLogger
    data_logger = DataLogger(csv_file, port, sql_database)
    
    # Initialize the database (create table and columns if they don't exist)
    data_logger.init_database()
    
    INTERVAL = 10  # Default interval
    try:
        # Try to read the INTERVAL environment variable
        env_interval = os.environ.get('INTERVAL')
        
        # Convert to float if the variable exists and is a valid integer
        if env_interval is not None:
            INTERVAL = int(env_interval)
            print(f"Using INTERVAL environment variable: {INTERVAL} seconds.")
        else:
            print("INTERVAL environment variable not found. Using default 10 seconds.")
    except (TypeError, ValueError):
        print("Invalid INTERVAL environment variable. Using default 10 seconds.")


    def read_and_write():
        """Read values from sensors and write them to the database."""
        # Schedule the next execution
        threading.Timer(INTERVAL, read_and_write).start()
        
        try:
            # Read values from the sensors
            values = data_logger.read_values()
            
            # Print the values for verification
            data_logger.print_values(values)
            
            # Write the values to the database
            data_logger.write_to_database(values)
        except Exception as e:
            print(f"Error in read_and_write: {e}")


    read_and_write()

    print("Data logging started. Press Ctrl+C to stop.")

if __name__ == "__main__":
    main()
