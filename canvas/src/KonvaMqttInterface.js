/**
 * Control Konva.js stage using MQTT
 * Author: Tal Eisenberg (2023)
 */

import Konva from 'konva';

export const setupKonvaMQTTInterface = ({ mqtt, stage }) => {
    const tweens = {};
    const images = {};
    const videos = {};

    const get_node = (node_id) => {
        const node = (node_id === "stage") ? stage : stage.findOne('#' + node_id);
        if (!node) {
            throw Error(`Unknown node id '${node_id}'`)
        }
        return node;
    };

    const get_tween = (tween_id) => {
        const tween = tweens[tween_id];
        if (!tween) {
            throw Error(`Unknown tween id '${tween_id}'`);
        }
        return tween;
    };

    const get_image = (image_id) => {
        const image = images[image_id];
        if (!image) {
            throw Error(`Unknown image id '${image_id}'`);
        }
        return image;
    };

    const get_video = (video_id) => {
        const video = videos[video_id];
        if (!video) {
            throw Error(`Unknown video id '${video_id}'`);
        }
        return video;
    }

    const call_method = (obj, method, args) => {
        const m = obj[method];

        if (!m) {
            throw Error(`Unknown method '${method}'`);
        }
        return m.apply(obj, args);
    };

    const set_prop = (obj, prop, value) => {
        const p = obj[prop];

        if (!p) {
            throw Error(`Unknown property '${prop}'`);
        }
        obj[prop] = value;
    }

    const get_prop = (obj, prop) => {
        const p = obj[prop];

        if (p === undefined) {
            throw Error(`Unknown property '${prop}'`);
        }
        return obj[prop];
    }

    const reset = () => {
        for (const id of Object.getOwnPropertyNames(images)) {
            delete images[id];
        }
        for (const id of Object.getOwnPropertyNames(tweens)) {
            delete tweens[id];
        }
        for (const id of Object.getOwnPropertyNames(videos)) {
            delete videos[id];
        }

        stage.destroyChildren();
    };

    const { publish, publish_error, set_on_message } = mqtt;

    const mqtt_requests = {
        reset,
        on(payload) {
            const { node_id, event_name, handler_id } = payload;
            const node = get_node(node_id);
            if (!node) {
                return;
            }

            node.on(event_name, (e) => {
                publish("on", {
                    handler_id, event: e
                })
            })
        },

        off(payload) {
            const { node_id, event_name } = payload;
            const node = get_node(node_id);
            node.off(event_name);
        },

        add(payload) {
            const { container_id, node_class, node_config } = payload;
            if (node_config && node_config.image_id) {
                const image = get_image(node_config.image_id);
                node_config.image = image
                delete node_config.image_id
            }

            if (node_config && node_config.filters) {
                node_config.filters = node_config.filters.map((filter_name) => Konva.Filters[filter_name])
            }

            const container = get_node(container_id);
            container.add(new Konva[node_class](node_config))
        },

        node(payload) {
            const { node_id, method, args } = payload;
            const node = get_node(node_id)
            switch (method) {
                case "filters":
                    if (args.length > 0) {
                        args[0] = args[0].map((filter_name) => Konva.Filters[filter_name]);
                    }
                    break;
                case "moveTo":
                    if (args.length > 0) {
                        args[0] = get_node(args[0]);
                    }
                    break;
                case "fillPatternImage":
                    if (args.length > 0) {
                        args[0] = get_image(args[0]);
                    }
                    break;
                case "findAncestor":
                case "findAncestors":
                    if (args.length > 2) {
                        args[2] = get_node(args[2]);
                    }
                    break;
                case "to":
                    throw Error("node.to() function is not supported. Please use make_tween instead.");
                default:
            }

            return call_method(node, method, args);
        },

        make_tween(payload) {
            const { tween_id, tween_config } = payload;
            if (!tween_config.node_id) {
                throw Error("node_id key is missing from tween config.")
            }
            const node = get_node(tween_config.node_id);
            tween_config.node = node;
            delete tween_config.node_id;

            if (tween_config.easing) {
                tween_config.easing = Konva.Easings[tween_config.easing];
            }

            tween_config.onUpdate = () => {
                if (payload.send_updates) {
                    publish("tween_on_update", { tween_id, node: node.toJSON() });
                }
            }
            tween_config.onFinish = () => {
                publish("tween_on_finish", { tween_id, node: node.toJSON() });
            };
            const tween = new Konva.Tween(tween_config);
            tweens[tween_id] = tween;
            return tween;
        },

        remove_tween(payload) {
            const { tween_id } = payload;
            delete tweens[tween_id];
        },

        tween(payload) {
            const { tween_id, method, args } = payload;

            const tween = get_tween(tween_id);
            call_method(tween, method, args);
        },

        load_image(payload) {
            const { image_id, src } = payload;
            const image = new Image();
            images[image_id] = image;

            image.onload = (e) => {
                publish("image_onload", {
                    image_id, event: e
                });
            };
            image.onerror = (e) => {
                publish("image_onerror", {
                    image_id, event: e
                });
            }
            image.src = src;
        },

        remove_image(payload) {
            const { image_id } = payload;
            delete images[image_id];
        },

        load_video(payload) {
            const { video_id, src, muted } = payload;
            const video = document.createElement('video');
            videos[video_id] = { video, anim: null };

            video.addEventListener('loadedmetadata', () => {
                publish("video_loadedmetadata", {
                    video_id, video: {
                        duration: video.duration,
                        width: video.videoWidth,
                        height: video.videoHeight,
                    }
                });
            });

            video.addEventListener('error', (e) => {
                console.log('video_error', video_id, e);
                publish("video_error", {
                    video_id, event: e
                });
            });

            video.addEventListener('ended', () => {
                // TODO: add all timestamps
                publish("video_on_ended", { video_id });
            });

            video.send_updates = !!payload.send_updates;
            video.src = src;
            video.muted = muted
        },

        add_video(payload) {
            const { container_id, video_id, node_config } = payload;
            const { video } = get_video(video_id);
            node_config.image = video;
            const container = get_node(container_id);
            container.add(new Konva.Image(node_config));

            const anim = new Konva.Animation(() => {
                if (video.send_updates) {
                    publish("video_on_update", { video_id, video_timestamp: video.currentTime });
                }
            }, container);
            videos[video_id].anim = anim;
        },

        remove_video(payload) {
            const { video_id } = payload;
            delete videos[video_id];
        },

        video_set_props(payload) {
            const { video_id, props } = payload;
            const { video } = get_video(video_id);
            Object.entries(props).forEach(([prop, value]) => set_prop(video, prop, value));
        },

        video_get_props(payload) {
            const { video_id, props: video_props } = payload;
            const { video } = get_video(video_id);
            const res = video_props.map((prop) => [prop, get_prop(video, prop)])
            return res;
        },

        play_video(payload) {
            const { video_id } = payload;
            const { video, anim } = get_video(video_id);
            video.play();
            if (anim) {
                anim.start();
            }
        },

        pause_video(payload) {
            const { video_id } = payload;
            const { video, anim } = get_video(video_id);
            video.pause();
            if (anim) {
                anim.stop();
            }
        },

        echo(payload) {
            return payload;
        },
    }

    set_on_message((topic, request) => {
        try {
            const result = mqtt_requests[topic](request);
            if (result instanceof Promise) {
                result.then((async_result) => publish("result", { result: async_result, topic, request: JSON.parse(JSON.stringify(request)) }));
            } else {
                publish("result", { result, topic, request })
            }

        } catch (error) {
            publish_error({ message: `Error running command '${topic}':`, error, topic, request });
        }
    });

    const on_window_resize = (size) => {
        publish("window_on_resize", size);
    };

    return { on_window_resize };
};


