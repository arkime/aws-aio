from typing import Dict

ISM_ID_HISTORY="history"
INDEX_PATTERN_HISTORY = f"{ISM_ID_HISTORY}_v*"

def get_user_history_ism_policy(history_days: int) -> Dict[str, any]:
    return {
        "policy": {
            "description": "Delete Arkime history indices",
            "default_state": "warm",
            "states": [
                {
                    "name": "warm",
                    "transitions": [
                        {
                            "state_name": "delete",
                            "conditions": {
                            "min_index_age": f"{history_days}d"
                            }
                        }
                    ]
                },
                {
                    "name": "delete",
                    "actions": [
                        {
                            "delete": {}
                        }
                    ]
                }
            ],
            "ism_template": [
                {
                    "index_patterns": [
                        INDEX_PATTERN_HISTORY
                    ],
                    "priority": 95
                }
            ]
        }
    }

ISM_ID_SESSIONS="sessions"
INDEX_PATTERN_SESSIONS = f"{ISM_ID_SESSIONS}3-*"

def get_sessions_ism_policy(hot_days: int, warm_days: int, replicas: int, merge_segments: int) -> Dict[str, any]:
    return {
        "policy": {
            "description": "Arkime sessions3 Policy",
            "default_state": "hot",
            "states": [
                {
                    "name": "hot",
                    "transitions": [
                        {
                            "state_name": "warm",
                            "conditions": {
                                "min_index_age": f"{hot_days}d"
                            }
                        }
                    ]
                },
                {
                    "name": "warm",
                    "actions": [
                        {
                            "retry": {
                                "count": 3,
                                "backoff": "exponential",
                                "delay": "1m"
                            },
                            "force_merge": {
                                "max_num_segments": merge_segments
                            }
                        },
                        {
                            "allocation": {
                                "require": {
                                    "molochtype": "warm"
                                },
                                "wait_for": True
                            }
                        },
                        {
                            "retry": {
                                "count": 3,
                                "backoff": "exponential",
                                "delay": "1m"
                            },
                            "replica_count": {
                                "number_of_replicas": replicas
                            }
                        }
                    ],
                    "transitions": [
                        {
                            "state_name": "delete",
                            "conditions": {
                                "min_index_age": f"{warm_days}d"
                            }
                        }
                    ]
                },
                {
                    "name": "delete",
                    "actions": [
                        {
                            "retry": {
                                "count": 3,
                                "backoff": "exponential",
                                "delay": "1m"
                            },
                            "delete": { }
                        }
                    ],
                    "transitions": [ ]
                }
            ],
            "ism_template": [
                {
                    "index_patterns": [
                        INDEX_PATTERN_SESSIONS
                    ],
                    "priority": 95
                }
            ]
        }
    }