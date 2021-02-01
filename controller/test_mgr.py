import multiprocessing.managers as managers
import logging
import flask
import json

logging.basicConfig(level=logging.INFO)
managers.BaseManager.register("config")
managers.BaseManager.register('state')
managers.BaseManager.register('image_sources')
managers.BaseManager.register('video_writers')
manager = managers.BaseManager(address=("", 50000), authkey=b"reptilearn")
manager.connect()

app = flask.Flask("API")

@app.route("/config")
def config():
    return json.dumps(manager.config()._getvalue())

@app.route("/video_stream/<int:idx>")
@app.route("/video_stream/<int:idx>/<int:width>/<int:height>")
def video_stream(idx, width=None, height=None):
    img_src = manager.image_sources()._getvalue()[idx]
    return flask.Response(
        img_src.stream_gen((width, height)),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )

@app.route("/stop_stream/<int:idx>")
def stop_stream(idx):
    img_src = manager.image_sources()._getvalue()[idx]
    img_src.is_streaming = False
    return flask.Response("ok")

@app.route("/video_writer/<int:idx>/<cmd>")
def video_writer(idx, cmd):
    vid_writer = manager.video_writers()._getvalue()[idx]
    if cmd == "start":
        vid_writer.start_writing()
    if cmd == "stop":
        vid_writer.stop_writing()
        
    return flask.Response("ok")

@app.route("/")
def root():
    return "API Running"

@app.after_request
def after_request(response):
    header = response.headers
    header["Access-Control-Allow-Origin"] = "*"
    return response


app.run()

