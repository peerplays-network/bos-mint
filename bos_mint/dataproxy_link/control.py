from bos_mint import Config
import requests


def get_replayable_incidents(filter, identifier, chain, target=None):
    proxy = Config.get("dataproxy_link", "proxies", identifier)
    replay_url = (
        proxy["endpoint"] + "/replay" +
        "?token=" + proxy["token"] +
        "&only_report=True" +
        "&restrict_witness_group=" + chain +
        "&name_filter=" + filter
    )
    if target is not None and not target == "All":
        replay_url = replay_url + "&target=" + target
    response = requests.get(replay_url, timeout=10)
    if not response.status_code == 200:
        raise Exception("Dataproxy appears down, status=" + str(response.status_code))
    json_response = response.json()

    if json_response.get("matched_targets", 0) == 0:
        raise Exception("The dataproxy has not found matching witness to replay to")
    if json_response.get("amount_incidents", 0) == 0:
        raise Exception("The dataproxy has not found any matching incidents to replay")
    return json_response["incidents"]


def replay_incidents(filter, identifier, chain, target=None):
    proxy = Config.get("dataproxy_link", "proxies", identifier)
    replay_url = (
        proxy["endpoint"] + "/replay" +
        "?token=" + proxy["token"] +
        "&restrict_witness_group=" + chain +
        "&name_filter=" + filter
    )
    if target is not None and not target == "All":
        replay_url = replay_url + "&target=" + target
    response = requests.get(replay_url, timeout=10)
    if not response.status_code == 200:
        raise Exception("Dataproxy appears down, status=" + str(response.status_code))
    json_response = response.json()

    if json_response.get("matched_targets", 0) == 0:
        raise Exception("The dataproxy has not found matching witness to replay to")
    if json_response.get("amount_incidents", 0) == 0:
        raise Exception("The dataproxy has not found any matching incidents to replay")
    return json_response["incidents"]
