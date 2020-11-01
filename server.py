import os
from flask import Flask, jsonify
SECRET_KEY = os.urandom(32)

from flask import render_template, redirect, url_for, request

from forms.interface_form import InterfaceForm
from db import Pump

app = Flask(__name__)
app.config["SECRET_KEY"] = SECRET_KEY

@app.route('/', methods=["GET", "POST"])
def index():
    form = InterfaceForm()
    if request.method == 'POST':
        #POST
        pump_id = int(request.form.get('pump_id'))
        flow_rate = int(request.form.get('flow_rate'))
        Pump.set_flow_rate(pump_id, flow_rate)
        pump = Pump.select().where(number=pump_id).get()
        duty_cycle = pump.duty_cycle
        d = {
            "pump": pump_id,
            "flow_rate": flow_rate,
            "duty_cycle": duty_cycle
        }
        return jsonify(d)
    else:
        #GET
        if request.accept_mimetypes.best == 'application/json':
            data = {
                "pumps": {
                    [
                        {
                            "name": pump.name,
                            "flow_rate": pump.flow_rate,
                            "duty_cycle": pump.cycle
                        } for pump in Pump.select()
                    ]
                }
            }
            return jsonify(data)
        else:
            data = {
                "pumps": {
                    pump.number: {
                        "name": pump.name,
                        "flow_rate": pump.flow_rate,
                        "duty_cycle": pump.cycle
                    } for pump in Pump.select()
                }
            }
            return render_template("dutycycle.html", form=form, **data)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
