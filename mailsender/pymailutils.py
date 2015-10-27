#!/usr/bin/env python
# coding:utf-8
import os
import codecs
import logging


class MailSender():
    template = 'mail -s "$(echo "%(subject)s\
    \nReply-to:%(reply_to)s\
    \nContent-Type:text/html;charset="utf-8"\
    \nContent-Disposition:inline\
    \nMIME-Version: 1.0")" %(mail_to)s<%(tmp_file)s'.replace('    ', '')
    template = 'mail -a "Content-Type:text/html;charset="utf-8" Content-Disposition:inline"\
    -a "From:%(mail_from_name)s <%(mail_from)s>"\
    -a "Reply-to:%(reply_to)s"\
    -s "%(subject)s" %(mail_to)s<%(tmp_file)s'.replace('    ', ' ')

    def __init__(self, subject, mail_to, msg, reply_to='', mail_from='', html=False):
        self.mail_from = mail_from or reply_to or 'noreplay@noreplay.com'
        self.mail_from_name = self.mail_from.split('@')[0]
        self.subject = subject
        self.reply_to = reply_to or self.mail_from
        # if replyto is not a mail address system will auto add @xxx.xxx
        # postfix.
        self.mail_to = mail_to
        self.msg = msg
        self.tmp_file = '_mailfile'
        self.html = html

    def __call__(self):
        tf = codecs.open(self.tmp_file, 'w', encoding='utf-8')
        tf.write(self.msg)
        tf.close()
        sh = self.template % self.__dict__
        if not self.html:
            sh = sh.replace('Content-Type:text/html;charset="utf-8" ', '')
        logging.warning("exec: %s", sh)
        os.popen(sh)
        os.remove(self.tmp_file)


if __name__ == "__main__":
    from optparse import OptionParser

    parser = OptionParser()
    parser.add_option("-s", "--subject", dest="subject", default="No Subject",
                      help="write subject")
    parser.add_option("-c", "--content", dest="content", default="No Content",
                      help="mail content")
    parser.add_option("-t", "--mailto", dest="mailto",
                      help="mail address")
    options, args = parser.parse_args()
    ms = MailSender(options.subject, options.mailto, options.content)()