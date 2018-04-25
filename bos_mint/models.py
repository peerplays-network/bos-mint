from . import db


class LocalProposal(db.Model):
    proposelIdentifier = db.Column(db.String(128), primary_key=True)
    reviewed = db.Column(db.Boolean, default=False)

    @classmethod
    def getAllAsList(cls):
        lpList = LocalProposal.query.all()
        return [x.proposelIdentifier for x in lpList]

    @classmethod
    def wasReviewed(cls, proposalId):
        # check if it exists
        lp = LocalProposal.query.get(proposalId)

        if lp is None:
            lp = LocalProposal(proposelIdentifier=proposalId, reviewed=True)
            db.session.add(lp)

        db.session.commit()


class ViewConfiguration(db.Model):
    name = db.Column(db.String(128), primary_key=True)
    key = db.Column(db.String(128), primary_key=True)
    value = db.Column(db.String(128))

    @classmethod
    def set(cls, name, key, value):
        if type(value) == bool:
            if value:
                value = 'True'
            else:
                value = 'False'

        # check if it exists
        vc = ViewConfiguration.query.filter_by(name=name, key=key).first()

        if vc is None:
            vc = ViewConfiguration(name=name, key=key, value=value)
            db.session.add(vc)
        else:
            vc.value = value

        db.session.commit()

    @classmethod
    def get(cls, name, key, default):
        # check if it exists
        vc = ViewConfiguration.query.filter_by(name=name, key=key).first()

        if vc is None:
            return default
        else:
            if type(default) is bool:
                if vc.value == 'True':
                    return True
                else:
                    return False

            return vc.value
