const RLInput = ({ children, ...props }) => (
    <input {...props}>{children}</input>
);

const TextInput = ({ children, ...props }) => (
    <RLInput type="text" {...props}>{children}</RLInput>
);

RLInput.TextInput = TextInput;

export default RLInput;