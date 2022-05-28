import ReactJson from "react-json-view";

const RLJsonEdit = (props) => (
    props.className ? (
        <div className={props.className}>
            <ReactJson {...props} style={Object.assign({fontFamily: 'Fira Mono', overflow: 'auto'}, props.style || {})}/>
        </div>
    ) : <ReactJson {...props} style={Object.assign({fontFamily: 'Fira Mono', overflow: 'auto'}, props.style || {})}/>
);

export { RLJsonEdit };
