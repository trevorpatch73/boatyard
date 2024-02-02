export FLASK_APP=application
flask db init
flask db migrate -m "doing things"
flask db upgrade


ssh-keyscan -t rsa github.com >> ~/.ssh/known_hosts


git branch -D aci_fabric_node_member_data_20240201_020701
git branch -D   aci_fabric_node_member_data_20240201_021106
git branch -D   aci_fabric_node_member_data_20240201_021435