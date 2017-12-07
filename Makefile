
CC = gcc
CPP = g++
PYTHON_VERSION = 3.5m
PYTHON_INCLUDE = /usr/include/python$(PYTHON_VERSION)

IDIRS = -I$(PYTHON_INCLUDE) -I.
DEFINES = -D_ISOC99_SOURCE -D_FILE_OFFSET_BITS=64 -D_LARGEFILE_SOURCE -D_POSIX_C_SOURCE=200112 -D_XOPEN_SOURCE=600 -DPIC -DZLIB_CONST -D_GNU_SOURCE=1 -D_REENTRANT -D__STDC_CONSTANT_MACROS
CFLAGS = -fomit-frame-pointer -fPIC -pthread -Wall -Wextra -DNDEBUG -O3 -g -rdynamic $(IDIRS) $(DEFINES)

LIBRARIES = -L/usr/lib -L/usr/lib/python$(PYTHON_VERSION)/config -L/usr/lib/x86_64-linux-gnu/ -lpython$(PYTHON_VERSION) -lboost_python-py35


CPPFLAGS = -std=c++11 $(CFLAGS)

LFLAGS = -lm -lstdc++ -llzma -lz -ldl -lpthread
LDFLAGS = $(LIBRARIES) $(LFLAGS)


SRC = ./src

SOURCES = $(wildcard $(SRC)/*.cpp) 

EXECUTABLE = ./libpydetector.so

OBJECTS = $(patsubst %.cpp,%.o,$(SOURCES))

all: $(SOURCES) $(EXECUTABLE)

%.o : %.c
	@echo Compiling: $< 
	@$(CC) $(CFLAGS) -c $< -o $@

%.o : %.cpp
	@echo Compiling: $< 
	@$(CPP) $(CPPFLAGS) -c $< -o $@

clean:
	rm -f $(OBJECTS)
	rm -f $(EXECUTABLE)

$(EXECUTABLE): $(OBJECTS)
	@echo Linking: $@
	@$(CPP) -shared -Wl,--export-dynamic $(OBJECTS) $(LDFLAGS) -o $@
	cp -f $(EXECUTABLE) ./detectionExample/$(EXECUTABLE)

