from peewee import Model, SqliteDatabase, FloatField, IntegerField

from duty_cycle_manager import DutyCycleManager
dc = DutyCycleManager()

db = SqliteDatabase('db.db')

class BaseModel(Model):
    class Meta:
        database = db

class FlowRate(BaseModel):
    flow_rate = FloatField(default=0.0)

    @classmethod
    def get_flow_rate(self):
        try:
            return FlowRate.select().order_by(FlowRate.id.desc()).get().flow_rate
        except FlowRate.DoesNotExist:
            FlowRate.create(flow_rate=0)
            return FlowRate.select().order_by(FlowRate.id.desc()).get().flow_rate

    @classmethod
    def set_flow_rate(self, flow_rate: int):
        dc.set_cycle(flow_rate)
        FlowRate.create(flow_rate=flow_rate)

class DutyCycle(BaseModel):
    cycle = IntegerField(default=0)

    @classmethod
    def get_cycle(self):
        try:
            return DutyCycle.select().order_by(DutyCycle.id.desc()).get().cycle
        except DutyCycle.DoesNotExist:
            DutyCycle.create(cycle=0)
            return DutyCycle.select().order_by(DutyCycle.id.desc()).get().cycle


    @classmethod
    def set_cycle(self, cycle: int):
        DutyCycle.create(cycle=cycle)

db.connect()
if __name__ == '__main__':
    db.create_tables([DutyCycle, FlowRate])
