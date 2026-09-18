"""Logica del servizio, indipendente da HTTP.

Le funzioni qui dentro non sanno nulla di FastAPI: ricevono dati, restituiscono
dati o alzano `AppError`. È ciò che permette di provarle senza avviare un server
e di riusarle sia dalle rotte sia dai job.
"""
