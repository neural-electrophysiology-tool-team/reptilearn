/**
 * Canvas MQTT client based on Paho MQTT
 * Author: Tal Eisenberg (2023)
 */

import Paho from 'paho-mqtt';

export const MQTT = (canvas_id, mqtt_address, on_connect, on_disconnect, on_failure) => {
    const incoming_topic = `canvas/${canvas_id}/in`;
    const outgoing_topic = `canvas/${canvas_id}/out`;
    const client = new Paho.Client(mqtt_address.host, mqtt_address.port, canvas_id);

    const make_message = (topic, payload, retained = false) => {
        const msg = new Paho.Message(JSON.stringify(payload))
        msg.destinationName = outgoing_topic + "/" + topic;
        msg.retained = retained;
        return msg;
    };

    const publish = (topic, payload, retained = false) => {
        payload.response_timestamp = Date.now() / 1000;
        // console.log("publishing payload", payload, "topic", topic)
        client.publish(make_message(topic, payload, retained));
    };

    const publish_error = (payload) => {
        if (payload.error) {
            payload.message += " " + payload.error.toString();
            delete payload.error
        }

        console.error(payload);
        publish("error", payload)
    }

    client.onConnectionLost = (resp) => {
        console.warn('MQTT connection lost', resp);
        on_disconnect?.();
    }

    client.connect({
        onSuccess() {
            console.log(`MQTT connected successfully to ${mqtt_address.host}:${mqtt_address.port}. Subscribing to incoming_topic '${incoming_topic}'`);
            client.subscribe(incoming_topic + '/#');
            publish("connected", { value: true }, true);
            on_connect?.();
        },
        onFailure() {
            console.error(`MQTT connection to ${mqtt_address.host}:${mqtt_address.port} failed.`)
            on_failure?.();
        },
        willMessage: make_message("connected", { value: false }, true),
    });

    const set_on_message = (on_message) => {
        client.onMessageArrived = (msg) => {
            // console.log('MQTT message arrived', msg);
            const topic = msg.topic.slice(incoming_topic.length + 1);
            try {
                const payload = JSON.parse(msg.payloadString);
                on_message?.(topic, payload)
            } catch (error) {
                publish_error({ message: "Error parsing payload:", error, payload: msg.payloadString })
            }
        };
    };

    return {
        mqtt: client,
        incoming_topic,
        outgoing_topic,
        publish,
        publish_error,
        set_on_message,
    }
};