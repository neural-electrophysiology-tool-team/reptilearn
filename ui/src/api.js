// To run a separate development http server set this flag to true:
const DEVELOPMENT_MODE = false;

// If ReptiLearn API uses a different port change it here:
export const api_url = DEVELOPMENT_MODE ? `http://${window.location.hostname}:3500` : '';
export const socketio_url = DEVELOPMENT_MODE ? `${window.location.hostname}:3500` : '';

export const request = async (route, params, method = "GET", body = null, json_body = false) => {
    if (!route.startsWith('/')) {
        route = '/' + route;
    }
    if (json_body) {
        body = JSON.stringify(body);
    }
    try {
        const url = params ? `${api_url}${route}?${params}` : `${api_url}${route}`;
        const response = await fetch(url, {
            method: method,
            ...(body && { body }),
            ...(json_body && {
                headers: {
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
            }),
        });
        if (response.ok) {
            return response;
        } else {
            const text = await response.text();
            console.error("Received non-OK response:", response, text);
            throw Error("Received non-OK response from server");
        }
    } catch (e) {
        console.error("Error during API request: ", e);
        throw e;
    }
};

export const requestJSON = async (route, params, method = "GET", body = null) => {
    const response = await request(route, params, method, body);
    return await response.json();
};

// API

export const api = {
    get_config(key) {
        return requestJSON(`/config/${key}`)
    },
    stop_stream(src_id) {
        return request(`/stop_stream/${src_id}`);
    },
    run_action(label) {
        return request(`/run_action/${label}`);
    },

    save_image(src_id, filename_prefix) {
        if (filename_prefix) {
            return request(`/save_image/${src_id}/${filename_prefix}`);
        } else {
            return request(`/save_image/${src_id}`);
        }        
    },

    system: {
        shutdown() {
            return requestJSON('/system/shutdown');
        },
        restart() {
            return requestJSON('/system/restart');
        },
    },

    video: {
        get_config() {
            return requestJSON('/video/get_config');
        },
        update_config(video_config) {
            return request('/video/update_config', null, "POST", video_config, true);
        },
        async shutdown() {
            try {
                return await request('/video/shutdown');
            } catch (e) {
                console.log('Error while shutting down video system:', e);
            }

        },
        list_image_classes() {
            return requestJSON("/video/list_image_classes")
        },
        image_class_params(cls) {
            return requestJSON(`/video/image_class_params/${cls}`);
        },
    },

    video_record: {
        start() {
            return request("/video_record/start")
        },
        stop() {
            return request("/video_record/stop");
        },
        start_trigger() {
            return request("/video_record/stop_trigger");
        },
        stop_trigger() {
            return request("/video_record/start_trigger");
        },
        select_source(src_id) {
            return request(`/video_record/select_source/${src_id}`)
        },
        unselect_source(src_id) {
            return request(`/video_record/unselect_source/${src_id}`)
        },
        set_prefix(prefix) {
            return request(`/video_record/set_prefix/${prefix}`)
        },

    },

    sessions: {
        archive: {
            copy(session_ids, archives) {
                return request("/sessions/archive/copy", null, "POST", {
                    archives: archives,
                    sessions: session_ids,
                }, true)
            },
        },
        delete(session_ids) {
            return request("/sessions/delete", null, "POST", session_ids, true);
        },
    },

    session: {
        params: {
            reset() {
                return request("/session/params/update", null, "POST");
            },
            update(params) {
                return request("/session/params/update", null, "POST", params, true);
            },
        },
        blocks: {
            reset_block(idx) {
                return request(`/session/blocks/update/${idx}`, null, "POST");
            },
            reset_all() {
                return request("/session/blocks/update", null, "POST");
            },
            update(blocks) {
                return request("/session/blocks/update", null, "POST", blocks, true);
            },
        },
        create(id, experiment) {
            return request("/session/create", null, "POST", {
                "id": id,
                "experiment": experiment
            }, true);
        },
        close() {
            return request("/session/close");
        },
        continue(id) {
            return request("/session/continue/" + id);
        },
        get_list() { 
            return requestJSON("/session/list");
        },
        run() {
            return request("/session/run");
        },
        stop() {
            return request("/session/stop");
        },
        next_block() {
            return request("/session/next_block");
        },
        next_trial() {
            return request("/session/next_trial");
        },
        reset_phase() {
            return request("/session/reset_phase");
        },
    },

    experiment: {
        get_list() {
            return requestJSON("/experiment/list");
        },
    },

    arena: {
        get_config() {
            return requestJSON("/arena/config");
        },
        update_config(arena_config) {
            return request('/arena/update_config', null, "POST", arena_config, true);
        },
        run_bridge() {
            return request("/arena/run_bridge");
        },
        restart_bridge() {
            return request("/arena/restart_bridge");
        },
        stop_bridge() {
            return request("/arena/stop_bridge");
        },
        get_ports() {
            return requestJSON("/arena/ports");
        },
        upload_program(port_name) {
            if (port_name) {
                return request(`/arena/upload_program/${port_name}`);
            } else {
                return request(`/arena/upload_program`);
            }
        },
        switch_display(value, display = null) {
            // TODO: test
            return request(`/arena/switch_display/${value}/${display}`);
        },
        poll() {
            return request("/arena/poll");
        },
        run_command(cmd) {
            return request("/arena/run_command", null, "POST", cmd, true);
        },
        request_values(iface) {
            return request("/arena/request_values/" + iface);
        },
    },

    log: {
        get_buffer() {
            return requestJSON('/log/get_buffer');
        },
        clear_buffer() {
            return request('/log/clear_buffer');
        },
    },

    task: {
        get_list() {
            return requestJSON("/task/list");
        },
        run(module, task) { 
            return request(`/task/run/${module}/${task}`);            
        },
        schedule(module, task, args) { 
            return request(`/task/schedule/${module}/${task}`, null, "POST", args, true);
        },
        get_scheduled_tasks() { 
            return requestJSON('/task/scheduled_tasks');
        },
        cancel(task_id) { 
            return request(`/task/cancel/${task_id}`);
        },
    },
}
