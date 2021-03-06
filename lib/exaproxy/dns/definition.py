# encoding: utf-8
"""
definition.py

Created by David Farrar on 2012-02-08.
Copyright (c) 2011-2013  Exa Networks. All rights reserved.
"""

import random
import dnstype

# OPCODE:  Operation Type, 4 bits
#	   0: QUERY,  Standary query		RFC 1035
#	   1: IQUERY, Inverse query		RFC 1035, RFC 3425
#	   2: STATUS, Server status request	RFC 1035
#	  3:
#	  4: Notify				RFC 1996
#	   5: Update				RFC 2136
#	   6: RESERVED
#	  ... RESERVED
#	  15: RESERVED


#OPCODE, AA, TC, RD, RA, Z, AD, CD, RCODE


class DNSBaseType:
	QR = None
	OPCODE = 0   # Operation type

	def __init__(self, identifier):
		self.identifier = identifier


class DNSRequestType(DNSBaseType):
	QR = 0      # Query
	OPCODE = 0  # Query

	resource_factory = dnstype.DNSTypeFactory()

	@property
	def query_len(self):
		return len(self.queries)

	def __init__(self, identifier, queries=[]):
		self.identifier = identifier
		self.queries = queries or []
		self.flags = 256  # recursion desired

	def addQuestion(self, querytype, question):
		q = self.resource_factory.createQuery(querytype, question)
		self.queries.append(q)

	def __str__(self):
		query_s = "\n\t ".join(str(q) for q in self.queries)

		return """DNS REQUEST %(id)s
QUERIES: %(queries)s""" % {'id':self.identifier, 'queries':query_s}



class DNSResponseType(DNSBaseType):
	QR = 1      # Response
	OPCODE = 0

	def __init__(self, identifier, complete, queries=[], responses=[], authorities=[], additionals=[]):
		ok = complete is True and None not in (identifier, queries, responses, authorities, additionals)

		self.identifier = identifier
		self.complete = bool(complete)
		self.queries = (queries or []) if ok else []
		self.responses = (responses or []) if ok else []
		self.authorities = (authorities or []) if ok else []
		self.additionals = (additionals or []) if ok else []

		if self.queries:
			query = self.queries[0]
			self.qtype = query.querytype
			self.qhost = query.question
		else:
			self.qtype = None
			self.qhost = None

	@property
	def query_len (self):
		return len(self.queries)

	@property
	def response_len (self):
		return len(self.responses)

	@property
	def authority_len (self):
		return len(self.authorities)

	@property
	def additional_len (self):
		return len(self.additionals)

	@property
	def resources (self):
		for resource in self.responses:
			yield resource

		for resource in self.authorities:
			yield resource

		for resource in self.additionals:
			yield resource

	def getResponse(self):
		info = {}

		for response in self.responses:
			info.setdefault(response.question, {}).setdefault(response.querytype, []).append(response.response)

		for response in self.authorities:
			info.setdefault(response.question, {}).setdefault(response.querytype, []).append(response.response)

		for response in self.additionals:
			info.setdefault(response.question, {}).setdefault(response.querytype, []).append(response.response)

		return info

	def extract(self, hostname, rdtype, info, seen=[]):
		data = info.get(hostname)

		if data:
			if rdtype in data:
				value = random.choice(data[rdtype])
			else:
				value = None
		else:
			value = None

		return value

	def getValue(self, question=None, qtype=None):
		if question is None or qtype is None:
			if self.queries:
				query = self.queries[0]

				if question is None:
					question = query.question

				if qtype is None:
					qtype = query.querytype

		info = self.getResponse()
		return qtype, self.extract(question, qtype, info)

	def getChainedValue(self):
		cname = None

		if self.queries:
			qtype = 'CNAME'
			question = self.queries[0].question

			while question is not None and qtype == 'CNAME':
				cname = question
				qtype, question = self.getValue(question, qtype)

		return self.getValue(cname)

	def getRelated (self):
		for response in self.responses:
			if response.querytype == 'CNAME':
				related = response.response
				break
		else:
			related = None

		return related

	def isComplete(self):
		return self.complete

	def __str__(self):
		query_s = "\n".join('\t' + str(q) for q in self.queries)
		response_s = "\n\t".join('\t' + str(r) for r in self.responses)
		authority_s = "\n\t".join('\t' + str(r) for r in self.authorities)
		additional_s = "\n\t".join('\t' + str(r) for r in self.additionals)

		return """DNS RESPONSE %(id)s
QUERIES: %(queries)s
RESPONSES: %(response)s
AUTHORITIES: %(authorities)s
ADDITIONAL: %(additional)s""" % {'id':self.identifier, 'queries':query_s, 'authorities':authority_s, 'additional':additional_s, 'response':response_s}
