import { classNames } from "./common";

const RLInput = ({ children, ...props }) => (
    <input {...props}>{children}</input>
);

const Text = ({ children, className, ...props }) => (
    <RLInput type="text" {...props} className={classNames(className, "border border-gray-300 rounded-[4px] px-2 text-sm")}>{children}</RLInput>
);

const TopBarText = ({ children, className, ...props }) => (
    <RLInput type="text" {...props} className={classNames(className, "border border-gray-300 px-2 text-sm")}>{children}</RLInput>
);

RLInput.Text = Text;
RLInput.TopBarText = TopBarText;

export default RLInput;