from peewee import Model, SqliteDatabase, FloatField, IntegerField, CharField

try:
    from duty_cycle_manager import DutyCycleManager
    dc = DutyCycleManager()
except ModuleNotFoundError:
    print("Can't find pi")

db = SqliteDatabase('db.db')

class BaseModel(Model):
    class Meta:
        database = db

class Pump(BaseModel):
    number = IntegerField(unique=True)
    name = CharField(unique=True)
    flow_rate = FloatField(default=0.0)
    cycle = IntegerField(default=0)

    @classmethod
    def get_pump(self, pump_number: int):
        try:
            return Pump.select().where(number=pump_number).get()
        except Pump.DoesNotExist:
            return Pump.select().where(number=pump_number).get()

    @classmethod
    def set_flow_rate(self, pump_number: int, flow_rate: int):
        Pump.update(flow_rate=flow_rate).where(number=pump_number)
        Pump.execute()

db.connect()
if __name__ == '__main__':
    db.create_tables([Pump])

    pump_count = Pump.select().count()
    names = ["PMW 1", "PMW 2", "PMW 3"]
    if pump_count == 0:
        for i in range(3):
            Pump.create(number=i, name=names[i], flow_rate=0, cycle=0)
