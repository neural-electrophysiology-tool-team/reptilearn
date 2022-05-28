import React from 'react';
import { useSelector, useDispatch } from 'react-redux';
import { SocketContext } from './socket';
import { library } from '@fortawesome/fontawesome-svg-core';
import { fas } from '@fortawesome/free-solid-svg-icons';
import { far } from '@fortawesome/free-regular-svg-icons';

import { setCtrlState, setVideoConfig } from './store/reptilearn_slice';
import { api_url } from './config';
import { MainView } from './views/main_view';

library.add(fas, far);

const App = () => {
    const ctrlState = useSelector((state) => state.reptilearn.ctrlState);
    const videoConfig = useSelector((state) => state.reptilearn.videoConfig);
    const dispatch = useDispatch();

    const socket = React.useContext(SocketContext);

    const handle_new_state = React.useCallback(new_state => {
        dispatch(setCtrlState(JSON.parse(new_state)));
    }, [dispatch]);

    const handle_disconnect = React.useCallback(() => dispatch(setCtrlState(null)), [dispatch]);

    // Display confirmation dialog before unloading page.
    // window.onbeforeunload = () => true;    

    React.useEffect(() => {
        socket.on("state", handle_new_state);
        socket.on("disconnect", handle_disconnect);
        socket.on("connect", () => {
        });
    }, [handle_disconnect, handle_new_state, socket]);

    const fetch_video_config = React.useCallback(() => {
        return fetch(api_url + '/video/get_config')
            .then((res) => res.json())
            .then((config) => dispatch(setVideoConfig(config)))
            .catch(err => {
                console.log(`Error while fetching video config: ${err}`);
                setTimeout(fetch_video_config, 5000);
            });
    }, [dispatch]);

    React.useEffect(() => {
        fetch_video_config();
    }, [fetch_video_config]);

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
