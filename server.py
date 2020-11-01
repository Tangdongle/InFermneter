import os
from flask import Flask

SECRET_KEY = os.urandom(32)

from flask import render_template, redirect, url_for, request

from forms.interface_form import InterfaceForm
from db import *

app = Flask(__name__)
app.config["SECRET_KEY"] = SECRET_KEY

@app.route('/', methods=["GET", "POST"])
def index():
    form = InterfaceForm()
    if request.method == 'POST':
        #POST
        flow_rate = int(request.form.get('flow_rate'))
        FlowRate.set_flow_rate(flow_rate)
        cycle = DutyCycle.get_cycle()
        d = {
            "flow_rate": flow_rate,
            "duty_cycle": cycle
        }
        return render_template("dutycycle.html", form=form, **d)
    else:
        #GET
        d = {
            "flow_rate": FlowRate.get_flow_rate(),
            "duty_cycle": DutyCycle.get_cycle()
        }
        return render_template("dutycycle.html", form=form, **d)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
