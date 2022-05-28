import { createSlice } from '@reduxjs/toolkit';

export const reptilearnSlice = createSlice({
    name: 'reptilearn',
    initialState: {
        ctrlState: null,
        videoConfig: null,
    },
    reducers: {
        setCtrlState: (state, action) => {
            state.ctrlState = action.payload;
        },
        setVideoConfig: (state, action) => {
            state.videoConfig = action.payload;
        }
    },
});

export const { setCtrlState, setVideoConfig } = reptilearnSlice.actions;

export default reptilearnSlice.reducer;