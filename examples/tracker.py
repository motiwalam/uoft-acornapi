import sys
import acornapi
import time
import smtplib

def stats_for_course(course_object):
    meetings = course_object['responseObject']['meetings']
    return {
        m['displayName']: {
            'enrollSpace': m['enrollSpace']
        }
        for m in meetings
    }

def all_stats(client, courses):
    return {
        c: stats_for_course(client.course_registration_info(*c))
        for c in courses
    }

def keys_changed(s1, s2):
    return [k for k in s2 if s1.get(k) != s2.get(k)]

def get_diff_msg(s1, s2):
    changed = keys_changed(s1, s2)
    return '\n'.join(f'{k}: {s1.get(k)} -> {s2.get(k)}' for k in changed)

def monitor(client, courses, period, onchange):
    stats = {}
    while True:
        new_stats = all_stats(client, courses)
        if new_stats != stats:
            onchange(keys_changed(stats, new_stats), get_diff_msg(stats, new_stats))

        stats = new_stats
        time.sleep(period)

def print_to_terminal(changed, diff_msg):
    print(f"status change for {list(map("".join, changed))}")
    print(diff_msg)

def email_from_to(server, sender, recips):
    def onchange(changed, diff_msg):
        server.sendmail(sender, recips, f'Subject: status change for {list(map("".join, changed))}\n\n{diff_msg}')
    
    return onchange

def all_of(*funcs):
    def onchange(changed, diff_msg):
        for f in funcs:
            f(changed, diff_msg)

    return onchange


# example usage
# python tracker.py <utorid> <acorn-pass> <sender-email> <gmail-pass> <recipients> <course_specs> ...
# <gmail-pass> needs to be a special app password generated in google account \
# <recipients> is a ":" separated list of emails (i.e "user1@gmail.com:user2@gmail.com")
# <course_specs> is a "-" separated list of course code, section code, session code (i.e "APM462H1-S-20251 CSC413H1-S-20251")
def main(utorid, password, sender, gmail_pass, recip_specs, *course_specs):
    courses = list(map(lambda x: tuple(x.split('-')), course_specs))
    recips = recip_specs.split(':')

    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(sender, gmail_pass)
    

    client = acornapi.ACORN(utorid, password)
    client.authorize()

    monitor(client, courses, 30, all_of(
        print_to_terminal,
        email_from_to(server, sender, recips)
    ))

if __name__ == "__main__":
    raise SystemExit(main(*sys.argv[1:]))