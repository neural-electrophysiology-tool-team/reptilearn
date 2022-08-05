import flask
import json
from configure import get_config
from json_convert import json_convert

import overlay
import task
import arena
import experiment
import video_system
import undistort
import image_utils
import rl_logging


def add_routes(app):
    log = rl_logging.get_main_logger()

    # Flask REST API
    @app.route("/config/<attribute>")
    def route_config(attribute):
        return flask.Response(
            json.dumps(getattr(get_config(), attribute), default=json_convert),
            mimetype="application/json",
        )

    def parse_image_request(src_id):
        swidth = flask.request.args.get("width")
        width = None if swidth is None else int(swidth)
        sheight = flask.request.args.get("height")
        height = None if sheight is None else int(sheight)

        # TODO: don't use video_system here --v
        if video_system._state.exists(("video", "image_sources", src_id)):
            src_config = video_system.video_config["image_sources"][src_id]
        else:
            src_config = None

        if (
            flask.request.args.get("undistort") == "true"
            and src_config is not None
            and "undistort" in src_config
        ):
            oheight, owidth = src_config["image_shape"][:2]
            undistort_config = get_config().undistort[src_config["undistort"]]
            undistort_mapping, _, _ = undistort.get_undistort_mapping(
                owidth, oheight, undistort_config
            )
        else:
            undistort_mapping = None

        return (width, height, undistort_mapping)

    def encode_image_for_response(img, width, height, undistort_mapping):
        if undistort_mapping is not None:
            img = undistort.undistort_image(img, undistort_mapping)

        return image_utils.encode_image(
            img,
            encoding=get_config().http_streaming["encoding"],
            encode_params=get_config().http_streaming["encode_params"],
            shape=(width, height),
        )

    @app.route("/image_sources/<src_id>/get_image")
    def route_image_sources_get_image(src_id):
        img, _ = video_system.image_sources[src_id].get_image(scale_to_8bit=True)
        enc_img = encode_image_for_response(img, *parse_image_request(src_id))
        return flask.Response(enc_img, mimetype="image/jpeg")

    @app.route("/image_sources/<src_id>/stream")
    def route_image_sources_stream(src_id):
        if src_id not in video_system.image_sources:
            return flask.Response("Unknown image source id", status=400)

        img_src = video_system.image_sources[src_id]

        frame_rate = int(
            flask.request.args.get(
                "frame_rate", default=get_config().http_streaming["frame_rate"]
            )
        )

        enc_args = parse_image_request(src_id)

        def flask_gen():
            # log.info(f"Starting new stream: {src_id}")
            gen = img_src.stream_gen(frame_rate, scale_to_8bit=True)

            try:
                while True:
                    try:
                        img, timestamp = next(gen)
                        img = overlay.apply_overlays(img, timestamp, src_id)
                        enc_img = encode_image_for_response(img, *enc_args)
                        yield (
                            b"--frame\r\n"
                            b"Content-Type: image\r\n\r\n"
                            + bytearray(enc_img)
                            + b"\r\n\r\n"
                        )
                    except StopIteration:
                        break
            finally:
                # log.info("Stopping stream")
                pass

        return flask.Response(
            flask_gen(),
            mimetype="multipart/x-mixed-replace; boundary=frame",
        )

    @app.route("/stop_stream/<src_id>")
    def route_stop_stream(src_id):
        if src_id in video_system.image_sources:
            img_src = video_system.image_sources[src_id]
            img_src.stop_streaming()
        return flask.Response("ok")

    @app.route("/save_image/<src_id>")
    def route_save_image(src_id):
        video_system.capture_images([src_id])
        return flask.Response("ok")

    @app.route("/run_action/<label>")
    def route_run_action(label):
        try:
            experiment.run_action(label)
            return flask.Response("ok")
        except Exception as e:
            log.exception(f"Exception while running action {label}:")
            flask.abort(500, e)

    @app.route("/state")
    def route_state():
        return flask.Response(
            # TODO: change this --v
            json.dumps(video_system._state.get_self(), default=json_convert),
            mimetype="application/json",
        )

    @app.route("/experiment/list")
    def route_experiment_list():
        return flask.jsonify(list(experiment.load_experiment_specs().keys()))

    # Session Routes

    @app.route("/session/create", methods=["POST"])
    def route_session_start():
        try:
            session = flask.request.json
            exp_interface = experiment.create_session(
                session["id"], session["experiment"]
            )
            return flask.jsonify(exp_interface)
        except Exception as e:
            log.exception("Exception while starting new session:")
            flask.abort(500, e)

    @app.route("/session/continue/<session_name>")
    def route_session_continue(session_name):
        try:
            experiment.continue_session(session_name)
            return flask.Response("ok")
        except Exception as e:
            log.exception("Exception while continuing session:")
            flask.abort(500, e)

    @app.route("/session/close")
    def route_session_close():
        try:
            experiment.close_session()
            return flask.Response("ok")
        except Exception as e:
            log.exception("Exception while closing session:")
            flask.abort(500, e)

    @app.route("/session/run")
    def route_session_run():
        try:
            experiment.run_experiment()
            return flask.Response("ok")
        except Exception as e:
            log.exception("Exception while running session:")
            flask.abort(500, e)

    @app.route("/session/stop")
    def route_session_stop():
        try:
            experiment.stop_experiment()
            return flask.Response("ok")
        except Exception as e:
            log.exception("Exception while ending session:")
            flask.abort(500, e)

    @app.route("/session/next_block")
    def route_session_next_block():
        try:
            experiment.next_block()
            return flask.Response("ok")
        except Exception as e:
            log.exception("Exception while moving to next block:")
            flask.abort(500, e)

    @app.route("/session/next_trial")
    def route_session_next_trial():
        try:
            experiment.next_trial()
            return flask.Response("ok")
        except Exception as e:
            log.exception("Exception while moving to next trial:")
            flask.abort(500, e)

    @app.route("/session/reset_phase")
    def route_session_reset_phase():
        try:
            experiment.set_phase(0, 0)
            return flask.Response("ok")
        except Exception as e:
            log.exception("Exception while resetting experiment phase:")
            flask.abort(500, e)

    @app.route("/session/params/update", methods=["POST"])
    def route_session_params_update():
        try:
            experiment.update_params(flask.request.json)
            return flask.Response("ok")
        except Exception as e:
            # s = state.get_self()
            # send_state(s, s)
            log.exception("Exception while updating params:")
            flask.abort(500, e)

    @app.route("/session/blocks/update", methods=["POST"])
    @app.route("/session/blocks/update/<idx>", methods=["POST"])
    def route_session_blocks_update(idx=None):
        try:
            if idx is not None:
                experiment.update_block(int(idx), flask.request.json)
            else:
                experiment.update_blocks(flask.request.json)

            return flask.Response("ok")
        except Exception as e:
            # s = state.get_self()
            # send_state(s, s)
            log.exception("Exception while updating blocks:")
            flask.abort(500, e)

    @app.route("/session/list")
    def route_session_list():
        try:
            sessions = experiment.get_session_list()
            return flask.jsonify(sessions)
        except Exception as e:
            log.exception("Exception while getting session list:")
            flask.abort(500, e)

    @app.route("/sessions/archive/<action>", methods=["POST"])
    def sessions_archive(action):
        try:
            archives = flask.request.json["archives"]
            sessions = flask.request.json["sessions"]
            experiment.archive_sessions(sessions, archives, move=(action == "move"))
            return flask.Response("ok")
        except Exception as e:
            log.exception("Exception while archiving sessions:")
            flask.abort(500, e)

    @app.route("/sessions/delete", methods=["POST"])
    def sessions_delete():
        try:
            sessions = flask.request.json
            experiment.delete_sessions(sessions)
            return flask.Response("ok")
        except Exception as e:
            log.exception("Exception while deleting sessions:")
            flask.abort(500, e)

    # Tasks Routes

    @app.route("/task/list")
    def route_task_list():
        return flask.jsonify(task.all_tasks())

    @app.route("/task/run/<module>/<fn>")
    def route_task_run(module, fn):
        try:
            task.run(module, fn)
            return flask.Response("ok")
        except Exception as e:
            log.exception("Exception while running task.")
            flask.abort(500, e)

    @app.route("/task/schedule/<module>/<fn>", methods=["POST"])
    def route_task_schedule(module, fn):
        try:
            task.schedule_task(module, fn, **flask.request.json)
            return flask.Response("ok")
        except Exception as e:
            log.exception("Exception while running task.")
            flask.abort(500, e)

    @app.route("/task/scheduled_tasks")
    def route_task_scheduled_tasks():
        return flask.jsonify(task.scheduled_tasks())

    @app.route("/task/cancel/<int:task_idx>")
    def route_task_cancel(task_idx):
        try:
            task.cancel_task(task_idx)
            return flask.Response("ok")
        except Exception as e:
            log.exception("Exception while cancelling task.")
            flask.abort(500, e)

    # Video Routes

    @app.route("/video/update_config", methods=["POST"])
    def route_update_config():
        try:
            video_system.update_video_config(flask.request.json)
            return flask.Response("ok")
        except Exception as e:
            log.exception("Exception while updating video config:")
            flask.abort(500, e)

    @app.route("/video/get_config")
    def route_video_get_config():
        try:
            return flask.jsonify(video_system.video_config)
        except Exception as e:
            log.exception("Exception while getting video config:")
            flask.abort(500, e)

    @app.route("/video/list_image_classes")
    def route_video_list_classes():
        try:
            return flask.jsonify(
                {
                    "image_sources": video_system.source_classes,
                    "image_observers": video_system.observer_classes,
                }
            )
        except Exception as e:
            log.exception("Exception while getting image classes list:")
            flask.abort(500, e)

    @app.route("/video/image_class_params/<cls>")
    def route_video_image_class_params(cls):
        try:
            return flask.jsonify(video_system.image_class_params[cls])
        except Exception as e:
            log.exception("Exception while getting image classes params:")
            flask.abort(500, e)

    @app.route("/video/shutdown")
    def route_video_shutdown():
        try:
            video_system.shutdown_video()
            return flask.Response("ok")
        except Exception as e:
            log.exception("Exception while shutting down video system:")
            flask.abort(500, e)

    @app.route("/video_record/select_source/<src_id>")
    def route_select_source(src_id):
        video_system.select_source(src_id)
        return flask.Response("ok")

    @app.route("/video_record/unselect_source/<src_id>")
    def route_unselect_source(src_id):
        video_system.unselect_source(src_id)
        return flask.Response("ok")

    @app.route("/video_record/<cmd>")
    def route_video_record(cmd):
        if cmd == "start":
            video_system.start_record()
        elif cmd == "stop":
            video_system.stop_record()

        return flask.Response("ok")

    @app.route("/video_record/start_trigger")
    def route_start_trigger():
        arena.start_trigger()
        return flask.Response("ok")

    @app.route("/video_record/stop_trigger")
    def route_stop_trigger():
        arena.stop_trigger()
        return flask.Response("ok")

    @app.route("/video_record/set_prefix/")
    @app.route("/video_record/set_prefix/<prefix>")
    def route_set_prefix(prefix=""):
        video_system.set_filename_prefix(prefix)
        return flask.Response("ok")

    # Arena Routes

    @app.route("/arena/config")
    def route_arena_config():
        return flask.jsonify(arena.get_interfaces_config())

    @app.route("/arena/run_command", methods=["POST"])
    def route_arena():
        try:
            command = flask.request.json[0]
            interface = flask.request.json[1]
            if len(flask.request.json) > 2:
                args = flask.request.json[2:]
            else:
                args = None

            arena.run_command(command, interface, args, False)
            return flask.Response("ok")
        except Exception as e:
            log.exception("Exception while running arena command:")
            flask.abort(500, e)

    @app.route("/arena/request_values")
    @app.route("/arena/request_values/<interface>")
    def route_arena_request_values(interface=None):
        arena.request_values(interface)
        return flask.Response("ok")

    @app.route("/arena/list_displays")
    def route_arena_list_displays():
        return flask.jsonify(get_config().arena["display"].keys())

    @app.route("/arena/switch_display/<int:on>")
    @app.route("/arena/switch_display/<int:on>/<display>")
    def route_arena_switch_display(on, display=None):
        arena.switch_display(on != 0, display)
        return flask.Response("ok")

    @app.route("/arena/poll")
    def route_arena_poll():
        arena.poll()
        return flask.Response("ok")

    @app.route("/log/get_buffer")
    def route_log_buffer():
        try:
            return flask.jsonify(rl_logging.get_log_buffer())
        except Exception as e:
            log.exception("Exception while getting log buffer:")
            flask.abort(500, e)

    @app.route("/log/clear_buffer")
    def route_log_clear_buffer():
        rl_logging.clear_log_buffer()
        return flask.Response("ok")

    @app.route("/")
    def root():
        return "ReptiLearn Controller"
