"""
.. module: hubcommander.command_plugins.repeat
    :platform: Unix
    :copyright: (c) 2017 by Netflix Inc., see AUTHORS for more
    :license: Apache, see LICENSE for more details.

.. moduleauthor:: Mike Grima <mgrima@netflix.com>
.. moduleauthor:: Duncan Godfrey @duncangodfrey
"""
import datetime

from hubcommander.bot_components.decorators import hubcommander_command
from hubcommander.bot_components.bot_classes import BotCommander
from hubcommander.bot_components.slack_comm import send_info, send_error, send_success

from louisebot.config import config
from louisebot.db import DBSession, User, Day, Presence, Expense

endpoint = config.get('default', 'endpoint')
bot_id = config.get(endpoint, 'bot_id')
start_string = '<@{0}>'.format(bot_id)


class CocottePlugin(BotCommander):
    def __init__(self):
        super().__init__()

        self.commands = {
            "!Balance": {
                "command": "!Balance",
                "func": self.balance,
                "help": "Affiche l'état actuel des comptes.",
                "user_data_required": True,
                "enabled": True
            },
            "!Manger": {
                "command": "!Manger",
                "func": self.manger,
                "help": "Pour dire 'Je mange ce midi !'",
                "user_data_required": True,
                "enabled": True
            },
            "!CancelManger": {
                "command": "!CancelManger",
                "func": self.cancelmanger,
                "help": "Pour dire 'Je mange PAS ce midi !'",
                "user_data_required": True,
                "enabled": True
            },
            "!QuiMange": {
                "command": "!QuiMange",
                "func": self.quimange,
                "help": "Liste les inscrits du midi.",
                "user_data_required": True,
                "enabled": True
            },
            "!Achat": {
                "command": "!Achat",
                "func": self.achat,
                "help": "Pour déclarer un achat.",
                "user_data_required": True,
                "enabled": True
            },
            "!ListAchat": {
                "command": "!ListAchat",
                "func": self.listachat,
                "help": "Pour lister les achats.",
                "user_data_required": True,
                "enabled": True
            },
            "!MyBalance": {
                "command": "!MyBalance",
                "func": self.mybalance,
                "help": "Liste les derniers repas / achats et affiche sa balance.",
                "user_data_required": True,
                "enabled": True
            },
            "!MealPrice": {
                "command": "!MealPrice",
                "func": self.mealprice,
                "help": "Estime le prix moyen d'un repas.",
                "user_data_required": True,
                "enabled": True
                },
            }

    def setup(self, *args):
        # Add user-configurable arguments to the command_plugins dictionary:
        #for cmd, keys in USER_COMMAND_DICT.items():
        #    self.commands[cmd].update(keys)
        pass

    @staticmethod
    def get_db_user(session, user):
        return session.query(User).filter(User.name == user).first()

    @staticmethod
    def get_db_day(session):
        today = datetime.date.today()
        return session.query(Day).filter(Day.date == today).first()

    @hubcommander_command(
        name="!Balance",
        usage="!Balance",
        description="Affiche les balances !",
        required=[],
    )
    def balance(self, data, user_data):
        session = DBSession()
        users = (session.query(User)
                .all())
        outputs = []
        outputs.append('Voici l\'état des compte chez Louise :')
        real_users = []
        for user in users:
            real_users.append({'name': user.name, 'balance': user.balance})

        for user in sorted(real_users, key=lambda x: x['balance']):
            outputs.append('{0} : balance à {1:.2f}'.format(user['name'], user['balance']))
        send_info(data['channel'], text='\n'.join(outputs), thread=data["ts"])

    @hubcommander_command(
        name="!Manger",
        usage="!Manger",
        description="Pour indiquer qu'on mange le midi !",
        required=[],
	optional=[
            dict(name="guest", properties=dict(nargs="?", default=0, type=int,
                                                help="Nombre d'invité avec vous")),
            dict(name="for_user", properties=dict(nargs="?", default=None, type=str,
                                                help="Annuler l'entrée d'un autre user"),
                 lowercase=True)
        ]
    )
    def manger(self, data, user_data, guest, for_user):

        session = DBSession()
        if guest < 0:
            send_error(data['channel'], "Touche à ton cul avec ton nombre négatif <@{0}> ;)".format(user_data['id']), markdown=True, thread=data["ts"])
            return


        day = self.get_db_day(session)
        if not day:
            day = Day(date=datetime.date.today())
            session.add(day)
            session.commit()

        outputs = []

        if for_user:
            user = self.get_db_user(session, for_user)
            from_user = self.get_db_user(session, user_data['name'])
        else:
            user = self.get_db_user(session, user_data['name'])

        if not user:
            send_error(data['channel'], 'Erreur il faut ```python manage.db sync``` d\'abort !', thread=data["ts"])

        presence = session.query(Presence).filter(
                Presence.user_id == user.id,
                Presence.day_id == day.id).first()


        if not presence:
            presence = Presence(user_id=user.id,
                                day_id=day.id,
                                meals=guest+1)
            session.add(presence)
            session.commit()

            if for_user:
                outputs.append("Demande enregistrée par <@{0}> pour <@{1}>".format(from_user.slackid, user.slackid))
                if guest > 0:
                    outputs.append("Je compterai {0} part(s)".format(guest+1))
            else:
                outputs.append("J'ai pris en compte ta demande <@{1}>".format(user_data['id']))
                if guest > 0:
                    outputs.append("Je te compterai {0} part ce jour".format(guest+1))
        else:
            if presence.meals != guest+1:
                presence.meals = guest+1
                session.add(presence)
                session.commit()

                if for_user:
                    if guest > 0:
                        outputs.append("Demande modifiée par <@{0}> pour <@{1}>, {2} invité(s) rajoutés".format(from_user.slackid, user.slackid, guest))
                    else:
                        outputs.append("Demande modifiée par <@{0}> pour <@{1}>, les invités ont été supprimés".format(from_user.slackid, user.slackid, guest))
                else:
                    if guest > 0:
                        outputs.append("J'ai modifié ta demande, et rajouté {0} invité(s) <@{1}>".format(guest, user.slackid))
                    else:
                        outputs.append("J'ai modifié ta demande, et enlevé les invités <@{1}>".format(guest, user.slackid))
            else:
                if for_user:
                    outputs.append("Rien n'a changé, <@{0}> était déjà inscrit <@{1}> :)".format(user.slackid, from_user.slackid))
                else:
                    outputs.append("Rien n'a changé, tu étais déjà inscrit <@{0}> :)".format(user.slackid))


        outputs.append("Si besoin tu peux !CancelManger ou !Manger avec des invités :)")
        if for_user:
            send_info(data['channel'], text='\n'.join(outputs), markdown=True, ephemeral_user=user.slackid)
            send_info(data['channel'], text='\n'.join(outputs), markdown=True, ephemeral_user=from_user.slackid)
        else:
            send_info(data['channel'], text='\n'.join(outputs), markdown=True, ephemeral_user=user_data["id"])
        data['text'] = '!QuiMange'
        self.quimange(data, user_data)

    @hubcommander_command(
        name="!CancelManger",
        usage="!CancelManger",
        description="Pour annuler une inscription !",
        required=[],
	optional=[
            dict(name="for_user", properties=dict(nargs="?", default=None, type=str,
                                                help="Annuler l'entrée d'un autre user"),
                 lowercase=True)
        ]
    )
    def cancelmanger(self, data, user_data, for_user):
        session = DBSession()

        day = self.get_db_day(session)
        if not day:
            day = Day(date=datetime.date.today())
            session.add(day)
            session.commit()

        outputs = []

        if for_user:
            user = self.get_db_user(session, for_user)
        else:
            user = self.get_db_user(session, user_data['name'])

        if not user:
            send_error(data['channel'], 'Erreur zjaifnazgoizangoiazg', thread=data["ts"])

        presence = session.query(Presence).filter(
                Presence.user_id == user.id,
                Presence.day_id == day.id).first()
        if not presence:
            if for_user:
                outputs.append("@{0} n'étais pas inscrit, pas de soucis <@{1}> !".format(user.name, user_data['id']))
            else:
                outputs.append("Tu n'étais pas inscrit, pas de soucis <@{0}> !".format(user_data['id']))
        else:
            session.query(Presence).filter_by(id=presence.id).delete()
            session.commit()
            if for_user:
                outputs.append("J'ai supprimé l'inscription de @{0}.".format(user.name))
            else:
                outputs.append("J'ai supprimé ta demande <@{0}>, dommage ça allait être trop bon !".format(user_data['id']))

            outputs.append("Si besoin tu !Manger à nouveau :)")
        send_info(data['channel'], text='\n'.join(outputs), markdown=True, ephemeral_user=user_data["id"])
        data['text'] = '!QuiMange'
        self.quimange(data, user_data)

    @hubcommander_command(
        name="!QuiMange",
        usage="!QuiMange",
        description="Liste les inscrits du midi.",
        required=[],
	optional=[],
    )
    def quimange(self, data, user_data):
        outputs = []
        session = DBSession()

        day = self.get_db_day(session)
        if not day:
            day = Day(date=datetime.date.today())
            session.add(day)
            session.commit()

        presences = session.query(Presence).filter(
                Presence.day_id == day.id).all()
        if not presences:
            outputs.append("Personne d'inscrit aujourd'hui, sniff :(")
        else:
            total = 0
            for presence in presences:
                user = presence.user
                total += presence.meals
                guest = presence.meals - 1
                if guest > 0:
                    outputs.append("{0} avec {1} invités".format(user.name, guest))
                else:
                    outputs.append(user.name)
            if total > 1:
                outputs.insert(0, "Ce midi, {0} personnes mangent:".format(total))
            else:
                outputs.insert(0, "Ce midi, {0} personne mange, bravo à lui !!".format(total))

        send_info(data['channel'], text='\n'.join(outputs), markdown=True)

    @hubcommander_command(
        name="!Achat",
        usage="!Achat",
        description="Pour déclarer un achat.",
        required=[
            dict(name="amount", properties=dict(type=float,
                                                help="Achat pour combient ?"),
                 )
        ],
	optional=[
            dict(name="description", properties=dict(nargs="?", default=None, type=str,
                                                help="Achat pour quoi ?"),
                 lowercase=False)
        ]
    )
    def achat(self, data, user_data, amount, description):

        session = DBSession()
        today = datetime.date.today()
        user = self.get_db_user(session, user_data['name'])

        expense = Expense(user_id=user.id, amount=amount, description=description)
        session.add(expense)
        session.commit()

        send_info(data['channel'], text='Achat enregistré !', markdown=True, thread=data["ts"])

    @hubcommander_command(
        name="!ListAchat",
        usage="!ListAchat",
        description="Liste les achats.",
        required=[],
	optional=[
            dict(name="history", properties=dict(nargs="?", default=7, type=int,
                                                help="Remonte 7 jours dans le temps par défaut.")),
            dict(name="for_user", properties=dict(nargs="?", default=None, type=str,
                                                help="Liste les achats d'un autre user."),
                 lowercase=True)
        ]
    )
    def listachat(self, data, user_data, history, for_user):

        session = DBSession()
        today = datetime.date.today()

        if history < 1:
            send_error(data['channel'], "Non non non, history doit être > 1 <@{0}> ;)".format(user_data['id']), markdown=True)
            return

        user = None
        if for_user:
            user = self.get_db_user(session, for_user)

            if not user:
                send_error(data['channel'], 'Erreur zjaifnazgoizangoiazg')

        delta = datetime.timedelta(days=history)
        start_date = today - delta

        query  = session.query(Expense).filter(
                Expense.date >= start_date)
        if user:
            query = query.filter(Expense.user_id == user.id)

        expenses = query.all()

        outputs = []
        if not expenses:
            if user:
                outputs.append("Pas d'achat dans les {0} derniers jours pour {1}.".format(history, user.name))
            else:
                outputs.append("Pas d'achat dans les {0} derniers jours.".format(history))
        else:
            if user:
                outputs.append("Liste des achats depuis {0} jours par {1} :".format(history, user.name))
            else:
                outputs.append("Liste des achats depuis {0} jours :".format(history))
            for expense in expenses:
                if user:
                    text = "- Le {0} : {1} €".format(expense.date, expense.amount)
                else:
                    text = "- {0}, le {1} : {2} €".format(expense.user.name, expense.date, expense.amount)
                if expense.description:
                    text += " pour {0}".format(expense.description)
                outputs.append(text)
        send_info(data['channel'], text='\n'.join(outputs), markdown=True, thread=data["ts"])

    @hubcommander_command(
        name="!MyBalance",
        usage="!MyBalance",
        description="Liste les derniers repas / achats et affiche sa balance.",
        required=[],
	optional=[
            dict(name="history", properties=dict(nargs="?", default=7, type=int,
                                                help="Remonte 7 jours dans le temps par défaut.")),
            dict(name="for_user", properties=dict(nargs="?", default=None, type=str,
                                                help="Pour afficher la balance d'un autre user"),
                 lowercase=True)
        ]
    )
    def mybalance(self, data, user_data, history, for_user):
        today = datetime.date.today()

        session = DBSession()
        if history < 1:
            send_error(data['channel'], "Non non non, history doit être > 1 <@{0}> ;)".format(user_data['id']), markdown=True)
            return

        if for_user:
            user = self.get_db_user(session, for_user)
        else:
            user = self.get_db_user(session, user_data['name'])

        if not user:
            send_error(data['channel'], 'Erreur zjaifnazgoizangoiazg')

        delta = datetime.timedelta(days=history)
        start_date = today - delta

        expenses = session.query(Expense).filter(
                Expense.user_id == user.id,
                Expense.date >= start_date).all()

        outputs = []
        if not expenses:
            outputs.append("Pas d'achat dans les {0} derniers jours pour {1}".format(history, user.name))
        else:
            if for_user:
                outputs.append("Liste des achats depuis {0} jours par {1} :".format(history, user.name))
            else:
                outputs.append("Liste de tes achats depuis {0} jours :".format(history))
            for expense in expenses:
                text = "- Le {0} : {1} €".format(expense.date, expense.amount)
                if expense.description:
                    text += " pour {0}".format(expense.description)
                outputs.append(text)

        presences = session.query(Presence).filter(Presence.user_id == user.id).join(Day).filter(Day.date >= start_date).all()

        if not presences:
            outputs.append("Pas de repas compatibilisé dans les {0} derniers jours pour {1}".format(history, user.name))
        else:
            if for_user:
                outputs.append("Liste des repas depuis {0} jours de {1} :".format(history, user.name))
            else:
                outputs.append("Liste de tes repas depuis {0} jours :".format(history))
            for presence in presences:
                text = "- Le {0} : {1} repas à {2} €".format(presence.day.date, presence.meals, presence.day.price)
                outputs.append(text)

        if for_user:
            outputs.append("Du coup, en tout, voici la balance de {0} : {1} €".format(user.name, user.balance))
        else:
            outputs.append("Du coup, en tout, voici ta balance : {0} €".format(user.balance))

        send_info(data['channel'], text='\n'.join(outputs), markdown=True, thread=data["ts"])

    @hubcommander_command(
        name="!MealPrice",
        usage="!MealPrice",
        description="Calcul le prix moyen d'un repas fonction des dépenses et des présences.",
        required=[],
	optional=[],
    )
    def mealprice(self, data, user_data):
        session = DBSession()

        total_expenses = 0.0
        expenses = session.query(Expense).all()
        for expense in expenses:
            total_expenses += expense.amount

        total_presences = 0
        presences = session.query(Presence).all()
        for presence in presences:
            total_presences += presence.meals
            
        average_price = total_expenses / total_presences

        outputs = []
        outputs.append("Total des dépenses : {0} €".format(total_expenses))
        outputs.append("Total de repas : {0}".format(total_presences))
        outputs.append("Prix moyen d'un repas : {0} €".format(average_price))

        send_info(data['channel'], text='\n'.join(outputs), markdown=True)
