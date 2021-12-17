from flask import render_template, flash, request
from wtforms import Form, validators, HiddenField, PasswordField

class PasswordResetForm(Form):   
    password = PasswordField('password', validators=[validators.InputRequired, validators.Length(min=6, max=100)])
    reset_token = HiddenField('reset_token')
