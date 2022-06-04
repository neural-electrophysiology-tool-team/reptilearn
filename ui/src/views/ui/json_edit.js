import ReactJson from "react-json-view";

const RLJsonEdit = ({ className, style, ...props }) => (
    className ? (
        <div className={className}>
            <ReactJson {...props} style={Object.assign({fontFamily: 'Fira Mono', overflow: 'auto'}, style || {})}/>
        </div>
    ) : <ReactJson {...props} style={Object.assign({fontFamily: 'Fira Mono', overflow: 'auto'}, style || {})}/>
);

export { RLJsonEdit };
