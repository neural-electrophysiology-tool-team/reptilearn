import { configureStore } from "@reduxjs/toolkit";
import reptilearnReducer from './reptilearn_slice';

export default configureStore({
    reducer: {
        reptilearn: reptilearnReducer,
    },
})