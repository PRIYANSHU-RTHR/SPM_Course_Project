from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.errors import NotFoundError, ValidationFailedError
from app.models import Availability, Member, MemberSkill, Skill
from app.schemas.member import (
    AvailabilityCreate,
    MemberCreate,
    MemberRead,
    MemberSkillIn,
    MemberSkillRead,
    MemberSkillsReplace,
    MemberUpdate,
)
from app.schemas.member import AvailabilityRead as AvailabilityReadSchema
from app.services.common import PageParams, apply_changes, commit, get_or_404, paginate

_LOAD = (
    selectinload(Member.skills).selectinload(MemberSkill.skill),
    selectinload(Member.availability),
)


def to_read(member: Member) -> MemberRead:
    return MemberRead(
        id=member.id,
        name=member.name,
        role=member.role,
        email=member.email,
        skills=sorted(
            (
                MemberSkillRead(skill_id=ms.skill_id, skill=ms.skill.name, level=ms.level)
                for ms in member.skills
            ),
            key=lambda s: s.skill,
        ),
        availability=[
            AvailabilityReadSchema.model_validate(a)
            for a in sorted(member.availability, key=lambda a: (a.start_date, a.id))
        ],
        created_at=member.created_at,
        updated_at=member.updated_at,
    )


def get_member(session: Session, member_id: int) -> Member:
    member = session.scalar(select(Member).where(Member.id == member_id).options(*_LOAD))
    if member is None:
        raise NotFoundError(f"Member {member_id} not found", details={"id": member_id})
    return member


def list_members(session: Session, page: PageParams) -> tuple[list[Member], int]:
    return paginate(session, select(Member).order_by(Member.id), page, options=_LOAD)


def _member_skills(session: Session, skills: list[MemberSkillIn]) -> list[MemberSkill]:
    ids = {s.skill_id for s in skills}
    known = set(session.scalars(select(Skill.id).where(Skill.id.in_(ids)))) if ids else set()
    unknown = sorted(ids - known)
    if unknown:
        raise ValidationFailedError("Unknown skill ids", details={"unknown_skill_ids": unknown})
    return [MemberSkill(skill_id=s.skill_id, level=s.level) for s in skills]


def create_member(session: Session, data: MemberCreate) -> Member:
    member = Member(name=data.name, role=data.role, email=data.email)
    member.skills = _member_skills(session, data.skills)
    member.availability = [Availability(**a.model_dump()) for a in data.availability]
    session.add(member)
    commit(session)
    return get_member(session, member.id)


def update_member(session: Session, member_id: int, data: MemberUpdate) -> Member:
    member = get_member(session, member_id)
    apply_changes(member, data.changes())
    commit(session)
    return get_member(session, member_id)


def delete_member(session: Session, member_id: int) -> None:
    """Fails with 409 if the member has assignment history (FK is RESTRICT)."""
    session.delete(get_or_404(session, Member, member_id, "Member"))
    commit(session)


def replace_skills(session: Session, member_id: int, data: MemberSkillsReplace) -> Member:
    member = get_member(session, member_id)
    new_skills = _member_skills(session, data.skills)
    member.skills.clear()
    session.flush()  # delete old rows before inserting, so unique(member, skill) holds
    member.skills.extend(new_skills)
    commit(session)
    return get_member(session, member_id)


def add_availability(session: Session, member_id: int, data: AvailabilityCreate) -> Member:
    member = get_member(session, member_id)
    member.availability.append(Availability(**data.model_dump()))
    commit(session)
    return get_member(session, member_id)


def delete_availability(session: Session, member_id: int, availability_id: int) -> None:
    availability = session.get(Availability, availability_id)
    if availability is None or availability.member_id != member_id:
        raise NotFoundError(
            f"Availability {availability_id} not found for member {member_id}",
            details={"id": availability_id, "member_id": member_id},
        )
    session.delete(availability)
    commit(session)
