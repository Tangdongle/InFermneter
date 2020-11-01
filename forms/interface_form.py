from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField
from wtforms.validators import NumberRange, ValidationError

class InterfaceForm(FlaskForm):
    pump_id = IntegerField('pump_id', validators=[NumberRange()])
    flow_rate = IntegerField('flow_rate', validators=[NumberRange()])

    def validate_flow_rate(form, field):
        flow_rate = 0
        try:
            flow_rate = int(field)
        except ValueError:
            raise ValidationError("Must input numbers")
