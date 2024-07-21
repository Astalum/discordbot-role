FROM Python:3.11.9

WORKDIR /home/astalum/

COPY /home/astalum/discordbot/konsei/discordbot-attend /home/astalum/

RUN pip install -r requirements.txt

CMD ["python3", "main.py"]