import websocket
import json
import time
import requests
from threading import Thread

class Fastcord:

    def __init__(self, token, verbose=False, on_message=None, on_event=None):
        self.token = token
        self.verbose = verbose
        self.ws = websocket.WebSocketApp("wss://gateway.discord.gg/?v=6&encoding=json",
            on_message=lambda ws, msg: self.on_message(ws, msg))
        self.resume = False
        self.seq = None
        self.last_msg = None
        self.interval = None
        self.session_id = None
        self.ready = False
        self.events = {
            "message": on_message,
            "event": on_event
        }
    
    def run(self):
        self.ws.run_forever()
    
    def heartbeat(self):
        while True:
            if self.verbose:
                print("[sending heartbeat]")
            
            self.ws.send(json.dumps({ "op": 1, "d": self.seq }))

            # if self.last_msg["op"] != 11 and self.ready:
            #     self.ws.close()
            #     self.resume = True
            #     self.ws.run_forever()

            time.sleep(self.interval / 1000 - 0.5)
    
    def send_message(self, contents, channel_id, embed = {}):
        r = requests.post(f"https://discordapp.com/api/channels/{channel_id}/messages",
            headers={ "Authorization": "Bot " + self.token },
            json={ "content": contents, "embed": embed })
        print(r.status_code)
    
    def on_message(self, ws, msg):
        if self.verbose:
            print("MESSAGE: " + msg)
        
        msg = json.loads(msg)
        self.last_msg = msg
        
        if msg["s"]:
            self.seq = msg["s"]
        else:
            self.seq = None
        
        if msg["op"] == 0:
            if self.events["event"] != None:
                    self.events["event"](msg)

            if msg["t"] == "READY":
                self.session_id = msg["d"]["session_id"]
                self.ready = True
            
            if msg["t"] == "MESSAGE_CREATE":
                if self.events["message"] != None:
                    self.events["message"](msg["d"])

        if msg["op"] == 9: # opcode 9 invalid session
            time.sleep(5)

            self.interval = msg["d"]["heartbeat_interval"]

            ws.send(json.dumps({
                "op": 2,
                "d": {
                    "token": self.token,
                    "properties": {
                        "$os": "linux",
                        "$browser": "fastcord",
                        "$device": "fastcord"
                    }
                }
            }))

        if msg["op"] == 10: # opcode 10 hello
            self.interval = msg["d"]["heartbeat_interval"]

            t = Thread(target=self.heartbeat)
            t.start()

            ws.send(json.dumps({
                "op": 2,
                "d": {
                    "token": self.token,
                    "properties": {
                        "$os": "linux",
                        "$browser": "fastcord",
                        "$device": "fastcord"
                    }
                }
            }))

            if self.resume:
                ws.send(json.dumps({
                    "op": 6,
                    "d": {
                        "token": self.token,
                        "session_id": self.session_id,
                        "seq": self.seq
                    }
                }))

                self.resume = False

        return