import React from 'react';
import { useSelector, useDispatch } from 'react-redux';
import { SocketContext } from './socket';
import { library } from '@fortawesome/fontawesome-svg-core';
import { fas } from '@fortawesome/free-solid-svg-icons';
import { far } from '@fortawesome/free-regular-svg-icons';

import { setCtrlState, setVideoConfig, setArenaConfig, setLog, setLogBufferLength, appendLog } from './store/reptilearn_slice';
import { MainView } from './views/main_view';
import { api } from './api';

library.add(fas, far);

const App = () => {
    const ctrlState = useSelector((state) => state.reptilearn.ctrlState);
    const videoConfig = useSelector((state) => state.reptilearn.videoConfig);
    const streams = useSelector((state) => state.reptilearn.streams);

    const dispatch = useDispatch();

    window.onbeforeunload = () => {
        streams.forEach((stream) => {
            if (stream.is_streaming) {
                api.stop_stream(stream.src_id);
            }
        });

        // Display confirmation dialog before unloading page.
        // return true;
    }

    const socket = React.useContext(SocketContext);

    const fetch_video_config = React.useCallback(() => {
        return api.video.get_config()
            .then((config) => dispatch(setVideoConfig(config)))
            .catch(err => {
                console.log(`Error while fetching video config: ${err}`);
                setTimeout(fetch_video_config, 5000);
            });
    }, [dispatch]);

    const fetch_arena_config = React.useCallback(() => {
        return api.arena.get_config()
            .then((config) => dispatch(setArenaConfig(config)))
            .catch(err => {
                console.log(`Error while fetching video config: ${err}`);
                setTimeout(fetch_arena_config, 5000);
            });
    }, [dispatch]);

    const fetch_log_buffer = React.useCallback(() => {
        api.log.get_buffer()
            .then((log_buffer) => {
                dispatch(setLog(log_buffer));
                return api.get_config('log_buffer_size');
            })
            .then((res) => res.json())
            .then((val) => {
                dispatch(setLogBufferLength(val));
            });
    }, [dispatch]);

    const handle_new_state = React.useCallback(new_state => {
        dispatch(setCtrlState(JSON.parse(new_state)));
    }, [dispatch]);

    const handle_disconnect = React.useCallback(() => {
        console.log("SocketIO disconnected.");
        dispatch(setCtrlState(null));        
    }, [dispatch]);

    const handle_connect = React.useCallback(() => {
        console.log("SocketIO connected.");
        fetch_video_config();
        fetch_arena_config();
        fetch_log_buffer();
    }, [fetch_arena_config, fetch_log_buffer, fetch_video_config]);

    const handle_log = React.useCallback((log_line) => {
        dispatch(appendLog(log_line));
    }, [dispatch]);

    React.useEffect(() => {
        if (socket.hasListeners('state')) {
            return;
        }

        socket.on("state", handle_new_state);
        socket.on("disconnect", handle_disconnect);
        socket.on("connect", handle_connect);
        socket.on("log", handle_log);
    }, [socket, handle_log, handle_connect, handle_disconnect, handle_new_state]);

    if (ctrlState === null || videoConfig === null)
        return (
            <div className="font-[Roboto] flex h-screen justify-center items-center">
                <div>
                    <div className="text-8xl mr-b-8 inline-block text-center">ReptiLearn</div>
                    <div className="text-2xl animate-pulse text-center">Waiting for connection...</div>
                </div>
            </div>
        );

    return <MainView/>
};

export default App;
