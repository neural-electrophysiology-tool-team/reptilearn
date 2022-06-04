import { ReflexContainer, ReflexSplitter, ReflexElement } from 'react-reflex';
import 'react-reflex/styles.css';

import { StreamGroupView } from './stream_view.js';
import { ExperimentView } from './experiment_view.js';
import { StateView } from './state_view.js';
import { LogView } from './log_view.js';
import { VideoRecordView } from './video_record_view.js';
import { ArenaControlView } from './arena_control_view.js';
import { SessionMenuView } from './session_menu_view.js';
import { TasksView } from './tasks_view.js';
import { AddStreamButton } from './add_stream_button.js';

export const TopBar = () => {
    return (
        <div className='border-b-2 border-b-gray-400 bg-gray-200 flex w-full overflow-visible text-sm'>
            <span className='px-1 font-bold flex items-center'>ReptiLearn</span>
            <VideoRecordView/>
            <TasksView/>
            <ArenaControlView/>
            <SessionMenuView/>
            <AddStreamButton/>
        </div>
    );
};

export const MainView = () => (
    <div className="text-sm flex flex-col h-screen">
        <TopBar></TopBar>
        <ReflexContainer orientation="horizontal" windowResizeAware={true} className='flex flex-grow'>
            <ReflexElement>
                <ReflexContainer orientation="vertical" windowResizeAware={true}>
                    <ReflexElement flex={0.65} className="bg-gray-700">
                        <StreamGroupView />
                    </ReflexElement>
                    <ReflexSplitter />
                    <ReflexElement minSize={422}>
                        <ReflexContainer orientation="horizontal">
                            <ReflexElement minSize={26} style={{ overflow: "hidden" }}>
                                <ExperimentView/>
                            </ReflexElement>
                            <ReflexSplitter />
                            <ReflexElement minSize={26} style={{ overflow: "hidden" }}>
                                <StateView/>
                            </ReflexElement>
                        </ReflexContainer>
                    </ReflexElement>
                </ReflexContainer>
            </ReflexElement>
            <ReflexSplitter />
            <ReflexElement minSize={26} flex={0.2} style={{ overflow: "hidden" }}>
                <LogView />
            </ReflexElement>
        </ReflexContainer>
    </div>
);