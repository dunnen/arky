# -*- encoding: utf8 -*-
# © Toons

from .. import __PY3__, setInterval, ArkyDict, ROOT, cfg, api, core, util, cli, slots
from yawTtk import dialog

import os, sys, yawTtk, json, webbrowser

class DataView(yawTtk.Tree):

	rows = []
	headers = []

	def __init__(self, parent=None, cnf={}, **kw):
		yawTtk.Tree.__init__(self, parent, cnf, **kw)
		self.tag_configure("even", background="lavender")
		self.tag_configure("odd", background="lightblue")
		self.__data_headings = []
		self.__sort_meaning = ""

	def populate(self, sortkey=None, meaning=None):
		# clear data
		self.delete(*self.xchildren())
		if DataView.rows == None:
			return
		# check witch meaning use
		if meaning == None:
			meaning = "ASC" if self.__sort_meaning == "DESC" else "DESC"
			self.__sort_meaning = meaning
		# sort data if asked
		if sortkey != None:
			rows = sorted(DataView.rows, key=lambda e:e.get(sortkey, ""), reverse=True if meaning == "ASC" else False)
		else:
			rows = DataView.rows
		# manage headers
		if not len(self.__data_headings):
			if len(DataView.headers): self.__data_headings = DataView.headers
			else: self.__data_headings = list(rows[0].keys())
			self['columns'] = " ".join(["{%s}"%h for h in self.__data_headings])
		for i in range(len(self.__data_headings)):
			text = self.__data_headings[i]
			self.heading("#%d"%(i+1), text=text, command=lambda o=self,k=text: o.populate(k,None))
			self.column("#%d"%(i+1), anchor="center", stretch=1)
		# populate data
		even=False
		for row in rows:
			self.insert(value=tuple(row.get(k, "") for k in DataView.headers), tag=("even",) if even else ("odd",))
			even = not even


class KeyDialog(dialog.BaseDialog):

	passphrase1 = None
	passphrase2 = None
	address = None
	check = True

	def fillMainFrame(self):
		self.transient(self.master)
		self.mainframe.columnconfigure(1, weight=1, minsize=300)
		self.mainframe.rowconfigure(1, weight=1)

		yawTtk.Label(self.mainframe, image=dialog.password, compound="image", padding=(0,0,4,0)).grid(row=0, rowspan=4, column=0, sticky="new")
		yawTtk.Label(self.mainframe, text="Main passphrase").grid(row=0, column=1, sticky="nesw")
		self.secret = yawTtk.Entry(self.mainframe, show="-").grid(row=1, column=1, sticky="new")
		self.secret.focus()

		self.secondsecret = yawTtk.Entry(self.mainframe, show="-")
		if api.Account.getAccount(KeyDialog.address, returnKey="account").get('secondPublicKey', False):
			yawTtk.Label(self.mainframe, text="Second passphrase").grid(row=2, column=1, sticky="nesw")
			self.secondsecret.grid(row=3, column=1, sticky="nesw")
			self.title("Two-secret secured account")
		else:
			self.title("Single-secret secured account")

	def fillButton(self):
		yawTtk.Button(self.buttonframe, font=("tahoma", 8, "bold"), image=dialog.cross16, compound="image",
		              background=self.background, style="Dialog.TButton", text="Cancel", width=-1,
		              command=self.destroy).pack(side="right")
		yawTtk.Button(self.buttonframe, font=("tahoma", 8, "bold"), image=dialog.tick16, compound="left",
		              background=self.background, style="Dialog.TButton", default="active", text="Sign transaction", width=-1,
		              command=self.link).pack(side="right", padx=self.border)
		b = yawTtk.Button(self.buttonframe, image=dialog.stop16, compound="left", text="Show",
		                  background=self.background, style="Dialog.Toolbutton", padding=(self.border, 0))
		b.pack(side="left", fill="y")
		b.bind("<ButtonPress>", lambda e,o=self: [o.secret.configure(show=""), o.secondsecret.configure(show="")])
		b.bind("<ButtonRelease>", lambda e,o=self: [o.secret.configure(show="-"), o.secondsecret.configure(show="-")])

	def show(self):
		KeyDialog.passphrase1 = None
		KeyDialog.passphrase2 = None
		dialog.BaseDialog.show(self)
		self.winfo_toplevel().wait_window(self)

	def link(self):
		self.destroy()
		if KeyDialog.passphrase1 == None:
			sys.stdout.write("No passphrase given")
		elif core.getAddress(core.getKeys(KeyDialog.passphrase1)) == KeyDialog.address:
			KeyDialog.check = True
		else:
			sys.stdout.write("Main passphrase mismatch")

	def destroy(self):
		KeyDialog.check = False
		passphrase1 = self.secret.get()
		passphrase2 = self.secondsecret.get()
		KeyDialog.passphrase1 = None if passphrase1 == "" else passphrase1
		KeyDialog.passphrase2 = None if passphrase2 == "" else passphrase2
		dialog.BaseDialog.destroy(self)


class AddressPanel(yawTtk.Frame):

	address = None

	def __init__(self, master=None, cnf={}, **kw):
		yawTtk.Frame.__init__(self, master, cnf={}, **kw)

		self.wallet = yawTtk.StringVar(self, "", "%s.wallet"%self._w)
		yawTtk.Label(self, font=("tahoma", 8, "bold"), text="Wallet address").grid(row=0, column=0, sticky="nesw", padx=4, pady=4)
		self.combo = yawTtk.Combobox(self, width=45, font=("courrier", "8", "bold"), textvariable=self.wallet).grid(row=0, column=1, sticky="nesw", padx=4, pady=4)

	def update(self, *args, **kw):
		value = self.wallet.get()
		if len(value) == 34:
			status = api.Account.getAccount(value)
			if status.success:
				AddressPanel.address = value
			else:
				sys.stdout.write("Account does not exists")
		else:
			AddressPanel.address = None

class AmountFrame(yawTtk.Frame):

	def __init__(self, master=None, cnf={}, **kw):
		yawTtk.Frame.__init__(self, master, cnf={}, **kw)
		self.columnconfigure(0, weight=0, minsize=35)
		self.columnconfigure(1, weight=1)
		self.columnconfigure(2, weight=0, minsize=120)

		self.amount = yawTtk.DoubleVar(self, 0., "%s.amount"%self._w)
		self.value = yawTtk.StringVar(self, u"\u0466 0.00000000", "%s.value"%self._w)
		self.what = yawTtk.StringVar(self, u"\u0466", "%s.what"%self._w)
		self.satoshi = 0

		yawTtk.Label(self, padding=2, text="amount", background="lightgreen", font=("tahoma", 8, "bold")).grid(row=0, column=0, columnspan=3, pady=4, sticky="nesw")
		yawTtk.Combobox(self, textvariable=self.what, state="readonly", values=(u"\u0466", "$", "€", "£", "¥", "%"), width=-1).grid(row=1, column=0, pady=4, sticky="nesw")
		yawTtk.Entry(self, textvariable=self.amount, justify="right").grid(row=1, column=1, padx=4, pady=4, sticky="nesw")
		yawTtk.Label(self, textvariable=self.value, relief="solid").grid(row=1, column=2, pady=4, sticky="nesw")

		self.amount.trace("w", self.update)
		self.what.trace("w", self.update)

	def update(self, *args, **kw):
		what = self.what.get()
		try:
			amount = self.amount.get()
		except:
			value = 0.
		else:
			if what == "%":
				value = (float(api.Account.getBalance(AddressPanel.address).get("balance", 0)) * amount/100 - cfg.__FEES__["send"])/100000000.
			elif what in ["$", "€", "£", "¥"]:
				price = util.getArkPrice({"$":"usd", "€":"eur", "£":"gbp", "¥":"cny"}[what])
				value = amount / price
			else:
				value = amount
		finally:
			self.satoshi = 100000000.*max(0., value)
			self.value.set("\u0466 %.8f" % value)

	def get(self): return self.satoshi


class SendPanel(yawTtk.Frame):
	
	def __init__(self, master=None, cnf={}, **kw):
		yawTtk.Frame.__init__(self, master, cnf={}, **kw)

		self.rowconfigure(6, weight=1)
		#
		yawTtk.Label(self, padding=2, text="recipientId", background="lightgreen", font=("tahoma", 8, "bold")).grid(row=0, column=0, columnspan=3, padx=4, pady=4, sticky="nesw")
		self.recipientId = yawTtk.Combobox(self).grid(row=1, column=0, columnspan=3, padx=4, pady=4, sticky="nesw")
		
		#
		yawTtk.Label(self, padding=2, text="vendorField", background="lightgreen", font=("tahoma", 8, "bold")).grid(row=2, column=0, columnspan=3, padx=4, pady=4, sticky="nesw")
		self.vendorField = yawTtk.Entry(self).grid(row=3, column=0, columnspan=3, padx=4, pady=4, sticky="nesw")
		
		#
		self.amount = AmountFrame(self, padding=(4,0,4,4), address=AddressPanel.address).grid(row=5, column=0, columnspan=3, sticky="nesw")
		#
		frame = yawTtk.Frame(self, padding=4, text="Send").grid(row=6, column=0, columnspan=3, sticky="esw")
		yawTtk.Separator(frame).pack(side="top", fill="x", pady=8)
		self.button = yawTtk.Button(frame, text="Send").pack(side="right")

		self.update()
		self.amount.value.trace("w", self.update)

	def update(self, *args, **kw):
		self.button.state("!disabled" if self.amount.satoshi > 0 else "disabled")

	def getTransaction(widget):
		recipientId = widget.recipientId.get()
		return core.Transaction(
			amount=widget.amount.get(),
			recipientId=recipientId,
			vendorField=widget.vendorField.get()
		)


class VotePanel(yawTtk.Frame):
	
	def __init__(self, master=None, cnf={}, **kw):
		yawTtk.Frame.__init__(self, master, cnf={}, **kw)

		self.columnconfigure(0, weight=1)
		self.rowconfigure(6, weight=1)

		self.username = yawTtk.StringVar(self, "", "vote.username")

		#
		self.candidates = api.Delegate.getCandidates()
		yawTtk.Label(self, padding=2, text="delegate", background="lightgreen", font=("tahoma", 8, "bold")).grid(row=0, column=0, columnspan=3, padx=4, pady=4, sticky="nesw")
		self.delegate = yawTtk.Combobox(self, values=tuple(d["username"] for d in self.candidates), textvariable="vote.username").grid(row=1, column=0, columnspan=3, padx=4, pady=4, sticky="nesw")
	
		#
		frame = yawTtk.Frame(self, padding=4, text="Send").grid(row=6, column=0, sticky="esw")
		yawTtk.Separator(frame).pack(side="top", fill="x", pady=8)
		self.button = yawTtk.Button(frame, text="").pack(side="right")

		self.update()
		@setInterval(5)
		def _update(obj): obj.update()
		self._stop__update = _update(self)

	def update(self):
		vote = api.Account.getVotes(AddressPanel.address, returnKey="delegates")
		if len(vote):
			self.delegate.set(vote[0]["username"])
			self.delegate.state("disabled")
			self.button["text"] = "Unvote"
			self.button.state("!disabled")
		else:
			self.delegate.state("!disabled")
			self.button["text"] = "Vote"
			self.button.state("disabled" if self.username.get() == "" else "!disabled")

	def getTransaction(widget):
		username = widget.username.get()
		if widget.button["text"] == "Unvote":
			return core.Transaction(
				type=3,
				recipientId = AddressPanel.address,
				asset=ArkyDict(votes=["-"+d["publicKey"] for d in widget.candidates if d["username"] == username])
			)
		else:
			return core.Transaction(
				type=3,
				recipientId = AddressPanel.address,
				asset=ArkyDict(votes=["+"+d["publicKey"] for d in widget.candidates if d["username"] == username])
			)

	def destroy(self):
		self._stop__update.set()
		yawTtk.Frame.destroy(self)


class TransactionPanel(yawTtk.Frame):

	def __init__(self, master=None, cnf={}, **kw):
		yawTtk.Frame.__init__(self, master, cnf={}, **kw)
		self.columnconfigure(0, weight=1)
		self.rowconfigure(0, weight=1)

		self.tree = DataView(self, padding=0, show="headings").grid(row=0, column=0, sticky="nesw")
		self.tree.bind("<Double-Button-1>", lambda e,obj=self:obj.openTx(e))

		yawTtk.Autoscrollbar(self, target=self.tree, orient="horizontal").grid(row=1, column=0, sticky="nesw")
		yawTtk.Autoscrollbar(self, target=self.tree, orient="vertical").grid(row=0, column=1, sticky="nesw")

		DataView.headers = ["id", "date", "type", "amount", "senderId", "recipientId", "vendorField"]

		self.update()
		@setInterval(20)
		def _update(obj): obj.update()
		self._stop__update = _update(self)

	def openTx(self, event):
		widget = event.widget
		values = widget.item(widget.identify("item", event.x, event.y), "values")
		if values: webbrowser.open(cfg.__EXPLORER__ + "/tx/" + values[0])

	def update(self):
		if AddressPanel.address != None:
			data1 = api.Transaction.getTransactionsList(senderId=AddressPanel.address, returnKey="transactions", limit=50, orderBy="timestamp:desc")
			data2 = api.Transaction.getTransactionsList(recipientId=AddressPanel.address, returnKey="transactions", limit=50, orderBy="timestamp:desc")
			if len(data1) + len(data2) > self.__last_number:
				self.__last_number = len(data1) + len(data2)
				typ = {0:"send", 1:"register 2nd secret", 2:"register delegate", 3:"vote", 4:""}
				data = []
				for row in data1:
					row["amount"] /= 100000000.
					row["date"] = slots.getRealTime(row.pop("timestamp"))
					row["type"] = typ[row["type"]]
					data.append(dict((k,v) for k,v in row.items() if k in DataView.headers))
				typ[0] = "receive"
				for row in [d for d in data2 if d["recipientId"] != d["senderId"]]:
					row["amount"] /= 100000000.
					row["date"] = slots.getRealTime(row.pop("timestamp"))
					row["type"] = typ[row["type"]]
					data.append(dict((k,v) for k,v in row.items() if k in DataView.headers))

				DataView.rows = sorted(data, key=lambda e:e["date"], reverse=True)
				self.tree.populate()
		else:
			self.tree.delete(*self.tree.xchildren())
			DataView.rows = []
			self.__last_number = 0


	def destroy(self):
		self._stop__update.set()
		yawTtk.Frame.destroy(self)

# # 
# class SharePanel(yawTtk.Frame):
	
# 	def __init__(self, master=None, cnf={}, **kw):
# 		AddressPanel.__init__(self, master, cnf={}, **kw)


class LogPanel(yawTtk.Frame):

	last_folder = ""
	
	def __init__(self, master, *args, **kw):
		yawTtk.Frame.__init__(self, master, padding=0, border=0, highlightthickness=0)
		self.columnconfigure(0, weight=1)
		self.rowconfigure(0, weight=1)

		self.listbox = yawTtk.Listbox(self, *args, **kw)
		self.listbox.grid(row=0, column=0, sticky="nesw")

		scrolly = yawTtk.Autoscrollbar(self, orient="vertical", target=self.listbox)
		scrolly.grid(row=0, column=1, sticky="ns")
		scrollx = yawTtk.Autoscrollbar(self, orient="horizontal", target=self.listbox)
		scrollx.grid(row=1, column=0, sticky="ew")

		self.menu = yawTtk.Menu(self, tearoff=False)
		def check_menu():
			value = "disabled" if len(self.listbox.get(0,"end")) <= 0 else "normal"
			self.menu.entryconfigure(0, state=value)
			self.menu.entryconfigure(1, state=value)
			self.menu.entryconfigure(3, state=value)
		self.menu["postcommand"] = check_menu

		self.menu.add("command", compound="left", ulabel="_Copy", command=self.copy, image=\
"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"\
"AABJRU5ErkJggg==")
		self.menu.add("command", compound="left", ulabel="_Save...", command=self.save, image=\
"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")
		self.menu.add("separator")
		self.menu.add("command", compound="left", ulabel="C_lear", command=lambda obj=self.listbox:obj.delete(0, "end"), image=\
"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")
		self.listbox.bind("<Button-3>", lambda event,obj=self.menu: obj.tk.eval("tk_popup %s %d %d" % (obj, event.x_root, event.y_root)))

	def copy(self):
		self.listbox.clipboard_clear()
		self.listbox.clipboard_append('\n'.join(self.listbox.get(0,"end")))

	def save(self):
		filepath = yawTtk.getSaveFile(
			self,
			defaultextension=".log",
			initialdir=Log.last_folder,
			title="Create log file",
			filetypes="{{Log file} {*.log}}"
		).decode()
		if filepath != "":
			out = open(filepath, "w")
			out.write('\n'.join(self.listbox.get(0,"end")))
			out.close()
			Log.last_folder = os.path.dirname(filepath)

	def write(self, *lines):
		for line in lines:
			for l in line.rstrip().split("\n"):
				self.listbox.insert("end", l.rstrip())
		self.update()
		self.listbox.see("end")

	def flush(self, *args, **kw):
		pass