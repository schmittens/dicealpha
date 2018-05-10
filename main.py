import asyncio
import websockets
import json
import random


url = 'wss://ws.dev.nuance.com/v2:443'
nmaid = 'NMDPTRIAL_christian_schilter_gmail_com20151216090339'
appkey = '097b759685bce396ccecf0394240710f3b2a3c72e176d7434da87b146d25b777a02c0d26e8f0bcb4dcaced1eec5f2d27896a9a6be071ae2d1a2a41874ff8fef0'


class DiceRollObject:
    url = 'wss://ws.dev.nuance.com/v2:443'

    message_connect = {
        "message": "connect",
        "codec": "audio/L16;rate=16000",
        "device_id": "1",
        "user_id": "1",
        "app_id": 'NMDPTRIAL_christian_schilter_gmail_com20151216090339',
        "app_key": '097b759685bce396ccecf0394240710f3b2a3c72e176d7434da87b146d25b777a02c0d26e8f0bcb4dcaced1eec5f2d27896a9a6be071ae2d1a2a41874ff8fef0'
    }

    query_begin = {
        "message": "query_begin",
        "context_tag": "dicealpha",
        "command": "NDSP_APP_CMD",
        "language": "eng-USA",
        "transaction_id": 2
    }

    query_parameter = {
        "message": "query_parameter",
        "parameter_name": "REQUEST_INFO",
        "parameter_type": "dictionary",
        "transaction_id": 2,
        "dictionary": {
            "application_data": {
                "text_input": ""
            }
        }
    }

    query_end = {
        "message": "query_end",
        "transaction_id": 2
    }

    def __init__(self, query):
        self.query = query
        self.query_parameter['dictionary']['application_data']['text_input'] = self.query
        self.mc = json.dumps(self.message_connect)
        self.qb = json.dumps(self.query_begin)
        self.qp = json.dumps(self.query_parameter)
        self.qe = json.dumps(self.query_end)
        self.dice = 20
        self.ndice = 1
        self.operator = "plus"
        self.modifier = 0

    def setResponse(self, response):
        self.response = response
        self.r = json.dumps(self.response)

    def processResponse(self, response):
        self.intent = response["nlu_interpretation_results"]["payload"]["interpretations"][0]["action"]["intent"]["value"]
        self.confidence = response["nlu_interpretation_results"]["payload"]["interpretations"][0]["action"]["intent"]["confidence"]
        self.dice = int(response["nlu_interpretation_results"]["payload"]["interpretations"][0]["concepts"]["DiceGroup"][0]["concepts"]["Dice"][0]["value"])

        try:
            self.ndice = int(response["nlu_interpretation_results"]["payload"]["interpretations"][0]["concepts"]["DiceGroup"][0]["concepts"]["nuance_CARDINAL_NUMBER"][0]["value"])
        except:
            pass

        try:
            self.operator = response["nlu_interpretation_results"]["payload"]["interpretations"][0]["concepts"]["Math"][0]["value"]
        except:
            pass

        try:
            self.modifier = int(response["nlu_interpretation_results"]["payload"]["interpretations"][0]["concepts"]["nuance_CARDINAL_NUMBER"][0]["value"])
        except:
            pass

    def diceRoll(self):
        tally = 0
        print("Rolling {0} d{1}".format(self.ndice, self.dice))
        for i in range(0, self.ndice):
            roll = random.randrange(1, self.dice+1)
            tally += roll
            print("Roll {0}: {1} | Total: {2}".format(i+1, roll, tally))

        if self.modifier >= 1:
            if self.operator == "plus":
                tally += self.modifier
                print("Adding {0}".format(self.modifier))
            elif self.operator == "minus":
                print("Subtracting {0}".format(self.modifier))
                tally -= self.modifier
            elif self.operator == "multiply":
                tally = tally * self.modifier
                print("Multiplying by {0}".format(self.modifier))
            elif self.operator == "divide":
                tally = tally / self.modifier
                print("Dividing by {0}".format(self.modifier))

        tally = int(round(tally, ndigits=0))
        print("Final result: {0}\n".format(tally))
        print("Confidence: {0}\n\n".format(self.confidence))

async def text_nlu(TextNLUObject):
    async with websockets.connect(TextNLUObject.url) as websocket:
        await websocket.send(TextNLUObject.mc)
        json_response = await websocket.recv()

        response = json.loads(str(json_response))

        if response["message"] == "connected":

            await websocket.send(TextNLUObject.qb)

            await websocket.send(TextNLUObject.qp)

            await websocket.send(TextNLUObject.qe)

            json_response = await websocket.recv()
            response = json.loads(str(json_response))

            if response["message"] == "query_error":
                print(response["reason"])

            else:
                TextNLUObject.setResponse(response)
                TextNLUObject.processResponse(response)
                return TextNLUObject


while True:
    query = input("Enter your roll: ")

    n = DiceRollObject(query)

    asyncio.get_event_loop().run_until_complete(text_nlu(n))

    n.diceRoll()

