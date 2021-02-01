import './App.css';
import React from 'react';

/*
TODO:
- stop stream before switching source.
- ui obviously.
- do something better when the api is not working (error of apiMsg).
- move image source ui to another component
- add a no image source option (default)
*/

const ImageSourceSelector = ({onSelect}) => {
    const [imageSources, setImageSources] = React.useState([]);

    React.useEffect(() => {
        fetch("http://localhost:5000/list_image_sources")
            .then(res => res.json())
            .then(
                (res) => {
                    setImageSources(res);
                },
                (error) => {
                    setImageSources([error.toString()]);
                }
            );
    }, []);

    const option_items = imageSources.map((src, idx) =>
        <option key={src} value={idx}>{src}</option>
    );

    return (
        <select onChange={onSelect}>
          {option_items}
        </select>
    );
};

const ImageSourceView = () => {
    const [isStreaming, setStreaming] = React.useState(false);
    const [curImageSource, setCurImageSource] = React.useState(0);

    const toggleStream = (e) => {
        if (isStreaming) {
            fetch(`http://localhost:5000/stop_stream/${curImageSource}`);
        }

        setStreaming(!isStreaming);
    };

    const startRecording = (e) => {
        fetch(`http://localhost:5000/video_writer/${curImageSource}/start`);
    };

    const stopRecording = (e) => {
        fetch(`http://localhost:5000/video_writer/${curImageSource}/stop`);
    };

    const onImageSourceSelect = (e) => {
        setCurImageSource(e.target.value);
    };
    
    const stream = isStreaming ?
	(
            <img
	      src={`http://localhost:5000/video_stream/${curImageSource}/640/480?${Date.now()}`}
              width="640"
              height="480"
            />
        ) : null;

    return (
	<div>
	  <label>Image source: </label>
          <ImageSourceSelector onSelect={onImageSourceSelect} />
	  <br/>
	  {stream}
          <br/>
          <button onClick={toggleStream}>Start/Stop Streaming</button>
          <button onClick={startRecording}>Start Recording</button>
          <button onClick={stopRecording}>Stop Recording</button>          
        </div>
    );
};

const App = () => {
    const [apiMsg, setApiMsg] = React.useState("not loaded yet.");
    
    React.useEffect(() => {
        fetch("http://localhost:5000/")
            .then(res => res.text())
            .then(
                (res) => {
		    setApiMsg(res);
		},
                (error) => {
		    setApiMsg(error.toString());
		}
	    );
    }, []);

    return (
        <div className="App">
          {apiMsg}<br/>
          <ImageSourceView/>
          <ImageSourceView/>
        </div>
    );
};

export default App;
