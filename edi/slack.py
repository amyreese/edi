# Copyright 2017 John Reese
# Licensed under the MIT license

import json
import slacker

from ent import Ent


class SlackerResponse(Ent):
    '''Ent subclass specific to Slack responses.'''

    pass


def slacker_ent_response(raw):
    '''Emulate the slacker Response type, but return a Ent instead for direct
    access to response values.'''

    body = json.loads(raw)
    response = SlackerResponse(body)
    response.raw = raw
    response.body = body
    response.successful = response.ok
    response.error = body.get('error')

    return response


slacker.Response = slacker_ent_response
