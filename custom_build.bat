pip freeze > lambda/api_state_machine/requirements.txt
cp lambda/api_state_machine/requirements.txt lambda/intake_context/requirements.txt
cp lambda/api_state_machine/requirements.txt lambda/issue_resolution_preapr/requirements.txt
cp lambda/api_state_machine/requirements.txt lambda/issue_resolution_postapr/requirements.txt
cp lambda/api_state_machine/requirements.txt lambda/ticketing/requirements.txt