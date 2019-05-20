from datetime import datetime


class Utility:
    def printit(self, text, status):
        now = datetime.now().strftime("%H:%M:%S ")
        print(now + ' ' + f'{text:60}' + '[ ' + status + ' ]')

    def check_testcase(self, result, testcase):
        if result == 0:
            self.printit(testcase, u'\u2714')
        else:
            self.printit(testcase, u'\u2718')
